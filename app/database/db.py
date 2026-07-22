import sqlite3
from pathlib import Path


class Database:

    def __init__(self):

        Path("data").mkdir(exist_ok=True)

        self.conn = sqlite3.connect(
            "data/facebook.db",
            check_same_thread=False
        )

        self.conn.row_factory = sqlite3.Row

        self.create_tables()
        self.migrate()

    # =====================================================

    def create_tables(self):

        self.conn.executescript("""

        CREATE TABLE IF NOT EXISTS accounts(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT,

            profile_path TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );

        ----------------------------------------------------

        CREATE TABLE IF NOT EXISTS groups(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            account_id INTEGER,

            name TEXT,

            url TEXT,

            group_uid TEXT,

            members TEXT,

            members_count INTEGER DEFAULT 0,

            privacy TEXT,

            category TEXT,

            selected INTEGER DEFAULT 1,

            active INTEGER DEFAULT 1,

            can_post INTEGER DEFAULT 1,

            last_scan TIMESTAMP,

            last_publish TIMESTAMP,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );

        ----------------------------------------------------

        CREATE TABLE IF NOT EXISTS publish_history(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            group_id INTEGER,
                               
            post_id INTEGER,

            status TEXT,

            message TEXT,

            published_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );

        ----------------------------------------------------
        CREATE TABLE IF NOT EXISTS posts(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT,

            content TEXT,

            image_path TEXT,

            video_path TEXT,

            youtube_url TEXT,

            tags TEXT DEFAULT '',

            status TEXT DEFAULT 'Draft',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP
        );

        ----------------------------------------------------
        CREATE TABLE IF NOT EXISTS schedules(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            post_id INTEGER,

            start_time TEXT,

            delay_seconds INTEGER,

            repeat_every INTEGER,

            enabled INTEGER DEFAULT 1

    );
        ----------------------------------------------------                                                
        CREATE TABLE IF NOT EXISTS settings(

            key TEXT PRIMARY KEY,

            value TEXT

        );

        """)

        self.conn.commit()

    # =====================================================

    def migrate(self):
        self._migrate_groups_unique_per_account()
        self._create_group_indexes()
        self._migrate_posts_library()
        self._create_post_indexes()

    def _migrate_groups_unique_per_account(self):
        if (
            not self._table_exists("groups")
            or (
                self._groups_unique_per_account()
                and not self._groups_has_global_url_unique()
            )
        ):
            return

        with self.conn:
            self.conn.execute("ALTER TABLE groups RENAME TO groups_old")
            self.conn.execute(
                """
                CREATE TABLE groups(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER,
                    name TEXT,
                    url TEXT,
                    group_uid TEXT,
                    members TEXT,
                    members_count INTEGER DEFAULT 0,
                    privacy TEXT,
                    category TEXT,
                    selected INTEGER DEFAULT 1,
                    active INTEGER DEFAULT 1,
                    can_post INTEGER DEFAULT 1,
                    last_scan TIMESTAMP,
                    last_publish TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.execute(
                """
                INSERT OR IGNORE INTO groups(
                    id,
                    account_id,
                    name,
                    url,
                    group_uid,
                    members,
                    members_count,
                    privacy,
                    category,
                    selected,
                    active,
                    can_post,
                    last_scan,
                    last_publish,
                    created_at
                )
                SELECT
                    id,
                    COALESCE(account_id, 1),
                    name,
                    url,
                    group_uid,
                    members,
                    COALESCE(members_count, 0),
                    privacy,
                    category,
                    COALESCE(selected, 1),
                    COALESCE(active, 1),
                    COALESCE(can_post, 1),
                    last_scan,
                    last_publish,
                    created_at
                FROM groups_old
                WHERE url IS NOT NULL
                ORDER BY id
                """
            )
            self.conn.execute("DROP TABLE groups_old")

    def _create_group_indexes(self):
        self.conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_groups_account_url
            ON groups(account_id, url)
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_groups_account_id
            ON groups(account_id)
            """
        )
        self.conn.commit()

    def _table_exists(self, table_name):
        row = self.conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table' AND name=?
            """,
            (table_name,),
        ).fetchone()
        return row is not None

    def _groups_unique_per_account(self):
        indexes = self.conn.execute("PRAGMA index_list(groups)").fetchall()

        for index in indexes:
            if not index[2]:
                continue

            columns = [
                column[2]
                for column in self.conn.execute(f"PRAGMA index_info({index[1]})").fetchall()
            ]

            if columns == ["account_id", "url"]:
                return True

        return False

    def _groups_has_global_url_unique(self):
        indexes = self.conn.execute("PRAGMA index_list(groups)").fetchall()

        for index in indexes:
            if not index[2]:
                continue

            columns = [
                column[2]
                for column in self.conn.execute(f"PRAGMA index_info({index[1]})").fetchall()
            ]

            if columns == ["url"]:
                return True

        return False

    def _migrate_posts_library(self):
        if not self._table_exists("posts"):
            return

        columns = {
            row[1]
            for row in self.conn.execute("PRAGMA table_info(posts)").fetchall()
        }

        migrations = {
            "tags": "ALTER TABLE posts ADD COLUMN tags TEXT DEFAULT ''",
            "status": "ALTER TABLE posts ADD COLUMN status TEXT DEFAULT 'Draft'",
            "updated_at": "ALTER TABLE posts ADD COLUMN updated_at TIMESTAMP",
        }

        for column, statement in migrations.items():
            if column not in columns:
                self.conn.execute(statement)

        self.conn.execute(
            """
            UPDATE posts
            SET updated_at=COALESCE(updated_at, created_at, CURRENT_TIMESTAMP),
                tags=COALESCE(tags, ''),
                status=COALESCE(NULLIF(status, ''), 'Draft')
            """
        )
        self.conn.commit()

    def _create_post_indexes(self):
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_posts_status
            ON posts(status)
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_posts_created_at
            ON posts(created_at)
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_posts_title
            ON posts(title)
            """
        )
        self.conn.commit()

    # =====================================================
    # GROUPS
    # =====================================================

    def upsert_group(
        self,
        account_id,
        name,
        url,
        members="",
        group_uid=None,
        members_count=0,
        privacy="",
        category="",
        selected=1,
        active=1,
        can_post=1
    ):

        self.conn.execute(
            """
            INSERT INTO groups(
                account_id,
                name,
                url,
                group_uid,
                members,
                members_count,
                privacy,
                category,
                selected,
                active,
                can_post,
                last_scan
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(account_id, url)
            DO UPDATE SET
                name=excluded.name,
                group_uid=COALESCE(excluded.group_uid, groups.group_uid),
                members=excluded.members,
                members_count=excluded.members_count,
                privacy=COALESCE(NULLIF(excluded.privacy, ''), groups.privacy),
                category=COALESCE(NULLIF(excluded.category, ''), groups.category),
                active=excluded.active,
                can_post=excluded.can_post,
                last_scan=CURRENT_TIMESTAMP
            """,
            (
                account_id,
                name,
                url,
                group_uid,
                members,
                members_count,
                privacy,
                category,
                int(selected),
                int(active),
                int(can_post),
            )
        )

        self.conn.commit()

    # =====================================================

    def save_group(self, account_id, name, url, members=""):
        self.upsert_group(
            account_id=account_id,
            name=name,
            url=url,
            members=members,
        )

    # =====================================================

    def get_groups(self, account_id=None):
        query = """
            SELECT *
            FROM groups
        """
        params = ()

        if account_id is not None:
            query += " WHERE account_id=?"
            params = (account_id,)

        query += " ORDER BY name"

        cur = self.conn.execute(
            query,
            params,
        )

        return cur.fetchall()

    # =====================================================

    def get_selected_groups(self, account_id=None):
        query = """
            SELECT *
            FROM groups
            WHERE selected=1
        """
        params = ()

        if account_id is not None:
            query += " AND account_id=?"
            params = (account_id,)

        query += " ORDER BY name"

        cur = self.conn.execute(
            query,
            params,
        )

        return cur.fetchall()

    # =====================================================

    def set_group_selected(
        self,
        group_id,
        selected
    ):

        self.conn.execute(
            """
            UPDATE groups
            SET selected=?
            WHERE id=?
            """,
            (
                int(selected),
                group_id
            )
        )

        self.conn.commit()

    # =====================================================

    def clear_groups(self):

        self.conn.execute(
            "DELETE FROM groups"
        )

        self.conn.commit()

    def clear_groups_for_account(self, account_id):
        self.conn.execute(
            """
            DELETE FROM groups
            WHERE account_id=?
            """,
            (account_id,),
        )
        self.conn.commit()

    def count_groups(self, account_id=None):
        return self._count_groups("1=1", account_id)

    def count_selected_groups(self, account_id=None):
        return self._count_groups("selected=1", account_id)

    def count_public_groups(self, account_id=None):
        return self._count_groups("LOWER(COALESCE(privacy, ''))='public'", account_id)

    def count_private_groups(self, account_id=None):
        return self._count_groups("LOWER(COALESCE(privacy, ''))='private'", account_id)

    def get_account_group_counts(self):
        cur = self.conn.execute(
            """
            SELECT
                accounts.id AS account_id,
                accounts.name AS account_name,
                COUNT(groups.id) AS group_count
            FROM accounts
            LEFT JOIN groups ON groups.account_id=accounts.id
            GROUP BY accounts.id, accounts.name
            ORDER BY accounts.name
            """
        )
        return cur.fetchall()

    def _count_groups(self, condition, account_id=None):
        query = f"SELECT COUNT(*) FROM groups WHERE {condition}"
        params = ()

        if account_id is not None:
            query += " AND account_id=?"
            params = (account_id,)

        return self.conn.execute(query, params).fetchone()[0]

    # =====================================================
    # POSTS
    # =====================================================

    def create_post(
        self,
        title="",
        content="",
        image_path="",
        video_path="",
        youtube_url="",
        tags="",
        status="Draft",
    ):
        cursor = self.conn.execute(
            """
            INSERT INTO posts(
                title,
                content,
                image_path,
                video_path,
                youtube_url,
                tags,
                status,
                updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                title,
                content,
                image_path,
                video_path,
                youtube_url,
                tags,
                status,
            ),
        )
        self.conn.commit()
        return self.get_post(cursor.lastrowid)

    def update_post(self, post_id, **fields):
        allowed = {
            "title",
            "content",
            "image_path",
            "video_path",
            "youtube_url",
            "tags",
            "status",
        }
        updates = {
            key: value
            for key, value in fields.items()
            if key in allowed
        }

        if not updates:
            return self.get_post(post_id)

        assignments = [f"{key}=?" for key in updates]
        assignments.append("updated_at=CURRENT_TIMESTAMP")
        values = list(updates.values())
        values.append(post_id)
        self.conn.execute(
            f"""
            UPDATE posts
            SET {", ".join(assignments)}
            WHERE id=?
            """,
            values,
        )
        self.conn.commit()
        return self.get_post(post_id)

    def delete_post(self, post_id):
        self.conn.execute(
            """
            DELETE FROM posts
            WHERE id=?
            """,
            (post_id,),
        )
        self.conn.commit()

    def archive_post(self, post_id):
        return self.update_post(post_id, status="Archived")

    def duplicate_post(self, post_id):
        post = self.get_post(post_id)

        if post is None:
            return None

        return self.create_post(
            title=f"{post['title']} Copy".strip(),
            content=post["content"],
            image_path=post["image_path"],
            video_path=post["video_path"],
            youtube_url=post["youtube_url"],
            tags=post["tags"],
            status="Draft",
        )

    def get_post(self, post_id):
        row = self.conn.execute(
            """
            SELECT *
            FROM posts
            WHERE id=?
            """,
            (post_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_posts(self, search=None, status=None, tag=None):
        query = """
            SELECT *
            FROM posts
            WHERE 1=1
        """
        params = []

        if search:
            query += """
                AND (
                    LOWER(COALESCE(title, '')) LIKE ?
                    OR LOWER(COALESCE(content, '')) LIKE ?
                    OR LOWER(COALESCE(tags, '')) LIKE ?
                )
            """
            pattern = f"%{search.lower()}%"
            params.extend([pattern, pattern, pattern])

        if status and status != "All":
            query += " AND status=?"
            params.append(status)

        if tag:
            query += " AND LOWER(COALESCE(tags, '')) LIKE ?"
            params.append(f"%{tag.lower()}%")

        query += " ORDER BY updated_at DESC, created_at DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def count_posts(self, status=None):
        query = "SELECT COUNT(*) FROM posts"
        params = ()

        if status and status != "All":
            query += " WHERE status=?"
            params = (status,)

        return self.conn.execute(query, params).fetchone()[0]

    # =====================================================
    # HISTORY
    # =====================================================

    def add_history(
        self,
        group_id,
        status,
        message=""
    ):

        self.conn.execute(
            """
            INSERT INTO publish_history
            (
                group_id,
                status,
                message
            )
            VALUES
            (
                ?,
                ?,
                ?
            )
            """,
            (
                group_id,
                status,
                message
            )
        )

        self.conn.commit()

    # =====================================================

    def get_history(self):

        cur = self.conn.execute(
            """
            SELECT *
            FROM publish_history
            ORDER BY published_at DESC
            """
        )

        return cur.fetchall()

    # =====================================================
    # SETTINGS
    # =====================================================

    def set_setting(
        self,
        key,
        value
    ):

        self.conn.execute(
            """
            INSERT INTO settings(key,value)
            VALUES(?,?)
            ON CONFLICT(key)
            DO UPDATE SET value=excluded.value
            """,
            (
                key,
                value
            )
        )

        self.conn.commit()

    # =====================================================

    def get_setting(
        self,
        key,
        default=None
    ):

        cur = self.conn.execute(
            """
            SELECT value
            FROM settings
            WHERE key=?
            """,
            (key,)
        )

        row = cur.fetchone()

        if row:
            return row["value"]

        return default

    # =====================================================

    def close(self):

        self.conn.close()
    def update_group_info(
    self,
    group_id,
    name,
    members,
    privacy
):
     self.conn.execute(
        """
        UPDATE groups
        SET
            name=?,
            members=?,
            privacy=?
        WHERE id=?
        """,
        (
            name,
            members,
            privacy,
            group_id
        )
    )

     
     self.conn.commit()

db = Database()
