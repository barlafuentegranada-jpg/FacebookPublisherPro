import json
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

            platform TEXT NOT NULL DEFAULT 'facebook',

            name TEXT,

            profile_path TEXT,

            status TEXT DEFAULT 'Login required',

            active INTEGER DEFAULT 1,

            last_login TIMESTAMP,

            publishing_state TEXT NOT NULL DEFAULT 'Available',

            publishing_state_updated_at TIMESTAMP,

            updated_at TIMESTAMP,

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

            account_id INTEGER NOT NULL,

            group_id INTEGER NOT NULL,
                               
            post_id INTEGER NOT NULL,

            campaign_id INTEGER NULL,

            status TEXT NOT NULL,

            message TEXT DEFAULT '',

            started_at TIMESTAMP,

            finished_at TIMESTAMP,

            published_post_url TEXT DEFAULT '',

            platform TEXT NOT NULL DEFAULT 'facebook',

            metadata TEXT DEFAULT '{}',

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

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

            supported_platforms TEXT DEFAULT '["facebook"]',

            platform_overrides TEXT DEFAULT '{}',

            media_type TEXT DEFAULT 'text',

            metadata TEXT DEFAULT '{}',

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

        ----------------------------------------------------
        CREATE TABLE IF NOT EXISTS campaigns(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            description TEXT DEFAULT '',

            status TEXT DEFAULT 'Draft',

            post_id INTEGER,

            delay_min_seconds INTEGER DEFAULT 0,

            delay_max_seconds INTEGER DEFAULT 0,

            stop_on_error INTEGER DEFAULT 0,

            stop_on_checkpoint INTEGER DEFAULT 1,

            continue_other_platforms_after_facebook_rate_limit INTEGER DEFAULT 0,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP,

            last_started_at TIMESTAMP,

            last_finished_at TIMESTAMP

        );

        ----------------------------------------------------
        CREATE TABLE IF NOT EXISTS campaign_accounts(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            campaign_id INTEGER NOT NULL,

            platform TEXT NOT NULL,

            account_id INTEGER NOT NULL,

            enabled INTEGER DEFAULT 1,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(campaign_id, platform, account_id)

        );

        ----------------------------------------------------
        CREATE TABLE IF NOT EXISTS campaign_targets(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            campaign_id INTEGER NOT NULL,

            platform TEXT NOT NULL,

            account_id INTEGER NOT NULL,

            target_id INTEGER NOT NULL,

            enabled INTEGER DEFAULT 1,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(campaign_id, platform, account_id, target_id)

        );

        ----------------------------------------------------
        CREATE TABLE IF NOT EXISTS campaign_runs(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            campaign_id INTEGER NOT NULL,

            status TEXT DEFAULT 'Running',

            total_targets INTEGER DEFAULT 0,

            processed_targets INTEGER DEFAULT 0,

            success_count INTEGER DEFAULT 0,

            failed_count INTEGER DEFAULT 0,

            skipped_count INTEGER DEFAULT 0,

            started_at TIMESTAMP,

            finished_at TIMESTAMP,

            message TEXT DEFAULT ''

        );

        ----------------------------------------------------
        CREATE TABLE IF NOT EXISTS campaign_run_items(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            campaign_run_id INTEGER NOT NULL,

            platform TEXT NOT NULL,

            account_id INTEGER NOT NULL,

            target_id INTEGER NOT NULL,

            post_id INTEGER NOT NULL,

            publish_history_id INTEGER,

            status TEXT DEFAULT 'Pending',

            message TEXT DEFAULT '',

            started_at TIMESTAMP,

            finished_at TIMESTAMP

        );

        ----------------------------------------------------
        CREATE TABLE IF NOT EXISTS telegram_accounts(

            account_id INTEGER PRIMARY KEY,

            bot_id TEXT DEFAULT '',

            bot_username TEXT DEFAULT '',

            encrypted_token_reference TEXT NOT NULL,

            status TEXT DEFAULT 'Disconnected',

            last_checked TIMESTAMP,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP

        );

        ----------------------------------------------------
        CREATE TABLE IF NOT EXISTS telegram_targets(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            account_id INTEGER NOT NULL,

            platform TEXT NOT NULL DEFAULT 'telegram',

            target_type TEXT NOT NULL,

            external_id TEXT NOT NULL,

            username TEXT DEFAULT '',

            name TEXT DEFAULT '',

            url TEXT DEFAULT '',

            selected INTEGER DEFAULT 1,

            active INTEGER DEFAULT 1,

            can_post INTEGER DEFAULT 0,

            member_count INTEGER DEFAULT 0,

            status TEXT DEFAULT '',

            metadata TEXT DEFAULT '{}',

            last_checked TIMESTAMP,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP,

            UNIQUE(account_id, external_id)

        );

        """)

        self.conn.commit()

    # =====================================================

    def migrate(self):
        self._migrate_accounts_platform()
        self._migrate_groups_unique_per_account()
        self._create_group_indexes()
        self._migrate_posts_library()
        self._create_post_indexes()
        self._migrate_publish_history()
        self._create_publish_history_indexes()
        self._migrate_campaigns()
        self._migrate_telegram()
        self._repair_false_publish_successes()

    def _migrate_accounts_platform(self):
        if not self._table_exists("accounts"):
            return

        columns = self._columns("accounts")
        migrations = {
            "platform": "ALTER TABLE accounts ADD COLUMN platform TEXT NOT NULL DEFAULT 'facebook'",
            "status": "ALTER TABLE accounts ADD COLUMN status TEXT DEFAULT 'Login required'",
            "active": "ALTER TABLE accounts ADD COLUMN active INTEGER DEFAULT 1",
            "last_login": "ALTER TABLE accounts ADD COLUMN last_login TIMESTAMP",
            "publishing_state": "ALTER TABLE accounts ADD COLUMN publishing_state TEXT NOT NULL DEFAULT 'Available'",
            "publishing_state_updated_at": "ALTER TABLE accounts ADD COLUMN publishing_state_updated_at TIMESTAMP",
            "updated_at": "ALTER TABLE accounts ADD COLUMN updated_at TIMESTAMP",
        }

        for column, statement in migrations.items():
            if column not in columns:
                self.conn.execute(statement)

        self.conn.execute(
            """
            UPDATE accounts
            SET platform=COALESCE(NULLIF(platform, ''), 'facebook'),
                 status=COALESCE(NULLIF(status, ''), 'Login required'),
                 publishing_state=COALESCE(NULLIF(publishing_state, ''), 'Available'),
                 active=COALESCE(active, 1),
                updated_at=COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
            """
        )
        self.conn.commit()

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

    def _columns(self, table_name):
        return {
            row[1]
            for row in self.conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }

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

        columns = self._columns("posts")

        migrations = {
            "tags": "ALTER TABLE posts ADD COLUMN tags TEXT DEFAULT ''",
            "status": "ALTER TABLE posts ADD COLUMN status TEXT DEFAULT 'Draft'",
            "updated_at": "ALTER TABLE posts ADD COLUMN updated_at TIMESTAMP",
            "supported_platforms": "ALTER TABLE posts ADD COLUMN supported_platforms TEXT DEFAULT '[\"facebook\"]'",
            "platform_overrides": "ALTER TABLE posts ADD COLUMN platform_overrides TEXT DEFAULT '{}'",
            "media_type": "ALTER TABLE posts ADD COLUMN media_type TEXT DEFAULT 'text'",
            "metadata": "ALTER TABLE posts ADD COLUMN metadata TEXT DEFAULT '{}'",
        }

        for column, statement in migrations.items():
            if column not in columns:
                self.conn.execute(statement)

        self.conn.execute(
            """
            UPDATE posts
            SET updated_at=COALESCE(updated_at, created_at, CURRENT_TIMESTAMP),
                tags=COALESCE(tags, ''),
                status=COALESCE(NULLIF(status, ''), 'Draft'),
                supported_platforms=COALESCE(NULLIF(supported_platforms, ''), '["facebook"]'),
                platform_overrides=COALESCE(NULLIF(platform_overrides, ''), '{}'),
                media_type=COALESCE(NULLIF(media_type, ''), 'text'),
                metadata=COALESCE(NULLIF(metadata, ''), '{}')
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

    def _migrate_publish_history(self):
        if not self._table_exists("publish_history"):
            return

        if self._publish_history_schema_is_current():
            return

        old_columns = self._columns("publish_history")

        def column(name, default):
            return name if name in old_columns else default

        created_source = "created_at" if "created_at" in old_columns else column("published_at", "CURRENT_TIMESTAMP")
        started_source = column("started_at", created_source)
        finished_source = column("finished_at", created_source)
        account_source = column("account_id", "0")
        group_source = column("group_id", "0")
        post_source = column("post_id", "0")
        campaign_source = column("campaign_id", "NULL")
        status_source = column("status", "'Failed'")
        message_source = column("message", "''")
        url_source = column("published_post_url", "''")
        platform_source = column("platform", "'facebook'")
        metadata_source = column("metadata", "'{}'")

        with self.conn:
            self.conn.execute("ALTER TABLE publish_history RENAME TO publish_history_old")
            self.conn.execute(
                """
                CREATE TABLE publish_history(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_id INTEGER NOT NULL,
                    group_id INTEGER NOT NULL,
                    post_id INTEGER NOT NULL,
                    campaign_id INTEGER NULL,
                    status TEXT NOT NULL,
                    message TEXT DEFAULT '',
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    published_post_url TEXT DEFAULT '',
                    platform TEXT NOT NULL DEFAULT 'facebook',
                    metadata TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.execute(
                f"""
                INSERT INTO publish_history(
                    id,
                    account_id,
                    group_id,
                    post_id,
                    campaign_id,
                    status,
                    message,
                    started_at,
                    finished_at,
                    published_post_url,
                    platform,
                    metadata,
                    created_at
                )
                SELECT
                    id,
                    COALESCE({account_source}, 0),
                    COALESCE({group_source}, 0),
                    COALESCE({post_source}, 0),
                    {campaign_source},
                    COALESCE(NULLIF({status_source}, ''), 'Failed'),
                    COALESCE({message_source}, ''),
                    {started_source},
                    {finished_source},
                    COALESCE({url_source}, ''),
                    COALESCE(NULLIF({platform_source}, ''), 'facebook'),
                    COALESCE(NULLIF({metadata_source}, ''), '{{}}'),
                    COALESCE({created_source}, CURRENT_TIMESTAMP)
                FROM publish_history_old
                ORDER BY id
                """
            )
            self.conn.execute("DROP TABLE publish_history_old")

    def _publish_history_schema_is_current(self):
        required = {
            "id": True,
            "account_id": True,
            "group_id": True,
            "post_id": True,
            "campaign_id": False,
            "status": True,
            "message": False,
            "started_at": False,
            "finished_at": False,
            "published_post_url": False,
            "platform": True,
            "metadata": False,
            "created_at": False,
        }
        rows = self.conn.execute("PRAGMA table_info(publish_history)").fetchall()
        columns = {row[1]: row for row in rows}

        for name, not_null in required.items():
            if name not in columns:
                return False

            if not_null and not columns[name][3] and name != "id":
                return False

        return True

    def _create_publish_history_indexes(self):
        indexes = [
            ("idx_publish_history_account_id", "account_id"),
            ("idx_publish_history_group_id", "group_id"),
            ("idx_publish_history_post_id", "post_id"),
            ("idx_publish_history_platform", "platform"),
            ("idx_publish_history_status", "status"),
            ("idx_publish_history_finished_at", "finished_at"),
            ("idx_publish_history_campaign_id", "campaign_id"),
        ]

        for name, column in indexes:
            self.conn.execute(
                f"""
                CREATE INDEX IF NOT EXISTS {name}
                ON publish_history({column})
                """
            )

        self.conn.commit()

    def _migrate_campaigns(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS campaigns(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                status TEXT DEFAULT 'Draft',
                post_id INTEGER,
                delay_min_seconds INTEGER DEFAULT 0,
                delay_max_seconds INTEGER DEFAULT 0,
                stop_on_error INTEGER DEFAULT 0,
                stop_on_checkpoint INTEGER DEFAULT 1,
                continue_other_platforms_after_facebook_rate_limit INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                last_started_at TIMESTAMP,
                last_finished_at TIMESTAMP
            )
            """
        )

        columns = self._columns("campaigns")
        migrations = {
            "description": "ALTER TABLE campaigns ADD COLUMN description TEXT DEFAULT ''",
            "delay_min_seconds": "ALTER TABLE campaigns ADD COLUMN delay_min_seconds INTEGER DEFAULT 0",
            "delay_max_seconds": "ALTER TABLE campaigns ADD COLUMN delay_max_seconds INTEGER DEFAULT 0",
            "stop_on_error": "ALTER TABLE campaigns ADD COLUMN stop_on_error INTEGER DEFAULT 0",
            "stop_on_checkpoint": "ALTER TABLE campaigns ADD COLUMN stop_on_checkpoint INTEGER DEFAULT 1",
            "continue_other_platforms_after_facebook_rate_limit": "ALTER TABLE campaigns ADD COLUMN continue_other_platforms_after_facebook_rate_limit INTEGER DEFAULT 0",
            "last_started_at": "ALTER TABLE campaigns ADD COLUMN last_started_at TIMESTAMP",
            "last_finished_at": "ALTER TABLE campaigns ADD COLUMN last_finished_at TIMESTAMP",
        }

        for column, statement in migrations.items():
            if column not in columns:
                self.conn.execute(statement)

        if "delay_min" in columns:
            self.conn.execute(
                """
                UPDATE campaigns
                SET delay_min_seconds=COALESCE(delay_min_seconds, delay_min, 0)
                """
            )

        if "delay_max" in columns:
            self.conn.execute(
                """
                UPDATE campaigns
                SET delay_max_seconds=COALESCE(delay_max_seconds, delay_max, 0)
                """
            )

        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS campaign_accounts(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(campaign_id, platform, account_id)
            );

            CREATE TABLE IF NOT EXISTS campaign_targets(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(campaign_id, platform, account_id, target_id)
            );

            CREATE TABLE IF NOT EXISTS campaign_runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id INTEGER NOT NULL,
                status TEXT DEFAULT 'Running',
                total_targets INTEGER DEFAULT 0,
                processed_targets INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                failed_count INTEGER DEFAULT 0,
                skipped_count INTEGER DEFAULT 0,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                message TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS campaign_run_items(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_run_id INTEGER NOT NULL,
                platform TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                publish_history_id INTEGER,
                status TEXT DEFAULT 'Pending',
                message TEXT DEFAULT '',
                started_at TIMESTAMP,
                finished_at TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
            CREATE INDEX IF NOT EXISTS idx_campaign_accounts_campaign_id ON campaign_accounts(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_campaign_accounts_platform ON campaign_accounts(platform);
            CREATE INDEX IF NOT EXISTS idx_campaign_accounts_account_id ON campaign_accounts(account_id);
            CREATE INDEX IF NOT EXISTS idx_campaign_targets_campaign_id ON campaign_targets(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_campaign_targets_platform ON campaign_targets(platform);
            CREATE INDEX IF NOT EXISTS idx_campaign_targets_account_id ON campaign_targets(account_id);
            CREATE INDEX IF NOT EXISTS idx_campaign_targets_target_id ON campaign_targets(target_id);
            CREATE INDEX IF NOT EXISTS idx_campaign_runs_campaign_id ON campaign_runs(campaign_id);
            CREATE INDEX IF NOT EXISTS idx_campaign_run_items_run_id ON campaign_run_items(campaign_run_id);
            CREATE INDEX IF NOT EXISTS idx_campaign_run_items_status ON campaign_run_items(status);
            CREATE INDEX IF NOT EXISTS idx_campaign_run_items_platform ON campaign_run_items(platform);
            CREATE INDEX IF NOT EXISTS idx_campaign_run_items_account_id ON campaign_run_items(account_id);
            CREATE INDEX IF NOT EXISTS idx_campaign_run_items_target_id ON campaign_run_items(target_id);
            """
        )
        self.conn.commit()

    def _migrate_telegram(self):
        if "metadata" not in self._columns("publish_history"):
            self.conn.execute("ALTER TABLE publish_history ADD COLUMN metadata TEXT DEFAULT '{}'")

        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_accounts(
                account_id INTEGER PRIMARY KEY,
                bot_id TEXT DEFAULT '',
                bot_username TEXT DEFAULT '',
                encrypted_token_reference TEXT NOT NULL,
                status TEXT DEFAULT 'Disconnected',
                last_checked TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
            """
        )
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telegram_targets(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                platform TEXT NOT NULL DEFAULT 'telegram',
                target_type TEXT NOT NULL,
                external_id TEXT NOT NULL,
                username TEXT DEFAULT '',
                name TEXT DEFAULT '',
                url TEXT DEFAULT '',
                selected INTEGER DEFAULT 1,
                active INTEGER DEFAULT 1,
                can_post INTEGER DEFAULT 0,
                member_count INTEGER DEFAULT 0,
                status TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}',
                last_checked TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(account_id, external_id)
            )
            """
        )
        self.conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_telegram_targets_account_id
            ON telegram_targets(account_id)
            """
        )
        self.conn.commit()

    def _repair_false_publish_successes(self):
        if not self._table_exists("publish_history"):
            return

        self.conn.execute(
            """
            UPDATE publish_history
            SET status='Validated'
            WHERE status='Success'
              AND LOWER(COALESCE(message, '')) LIKE '%dry run%'
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

    def count_accounts(self, platform=None):
        query = "SELECT COUNT(*) FROM accounts"
        params = []

        if platform:
            query += " WHERE platform=?"
            params.append(platform)

        return self.conn.execute(query, params).fetchone()[0]

    def set_account_publishing_state(self, account_id, publishing_state, updated_at=None):
        self.conn.execute(
            """
            UPDATE accounts
            SET publishing_state=?,
                publishing_state_updated_at=COALESCE(?, CURRENT_TIMESTAMP),
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (publishing_state, updated_at, account_id),
        )
        self.conn.commit()

    def count_accounts_requiring_review(self):
        return self.conn.execute(
            """
            SELECT COUNT(*)
            FROM accounts
            WHERE platform='facebook'
              AND publishing_state IN ('CoolingDown', 'RateLimited', 'ManualReviewRequired')
            """
        ).fetchone()[0]

    def count_targets(self, platform=None):
        if platform == "telegram":
            return self.conn.execute(
                """
                SELECT COUNT(*)
                FROM telegram_targets
                WHERE active=1
                """
            ).fetchone()[0]

        if platform and platform != "facebook":
            return 0

        total = self.count_groups()

        if platform is None:
            total += self.count_targets(platform="telegram")

        return total

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
    # CAMPAIGNS
    # =====================================================

    def create_campaign(
        self,
        name,
        description="",
        post_id=None,
        delay_min_seconds=0,
        delay_max_seconds=0,
        stop_on_error=False,
        stop_on_checkpoint=True,
        continue_other_platforms_after_facebook_rate_limit=False,
        status="Draft",
    ):
        cursor = self.conn.execute(
            """
            INSERT INTO campaigns(
                name,
                description,
                post_id,
                delay_min_seconds,
                delay_max_seconds,
                stop_on_error,
                stop_on_checkpoint,
                continue_other_platforms_after_facebook_rate_limit,
                status,
                updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                name,
                description,
                post_id,
                int(delay_min_seconds or 0),
                int(delay_max_seconds or 0),
                int(bool(stop_on_error)),
                int(bool(stop_on_checkpoint)),
                int(bool(continue_other_platforms_after_facebook_rate_limit)),
                status,
            ),
        )
        self.conn.commit()
        return self.get_campaign(cursor.lastrowid)

    def update_campaign(self, campaign_id, **fields):
        allowed = {
            "name",
            "description",
            "status",
            "post_id",
            "delay_min_seconds",
            "delay_max_seconds",
            "stop_on_error",
            "stop_on_checkpoint",
            "continue_other_platforms_after_facebook_rate_limit",
            "last_started_at",
            "last_finished_at",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}

        if not updates:
            return self.get_campaign(campaign_id)

        for key in [
            "stop_on_error",
            "stop_on_checkpoint",
            "continue_other_platforms_after_facebook_rate_limit",
        ]:
            if key in updates:
                updates[key] = int(bool(updates[key]))

        for key in ["delay_min_seconds", "delay_max_seconds"]:
            if key in updates:
                updates[key] = int(updates[key] or 0)

        assignments = [f"{key}=?" for key in updates]
        assignments.append("updated_at=CURRENT_TIMESTAMP")
        values = list(updates.values())
        values.append(campaign_id)
        self.conn.execute(
            f"""
            UPDATE campaigns
            SET {", ".join(assignments)}
            WHERE id=?
            """,
            values,
        )
        self.conn.commit()
        return self.get_campaign(campaign_id)

    def get_campaign(self, campaign_id):
        row = self.conn.execute(
            """
            SELECT *
            FROM campaigns
            WHERE id=?
            """,
            (campaign_id,),
        ).fetchone()
        return self._campaign_row(row) if row else None

    def get_campaigns(self, include_archived=False):
        query = "SELECT * FROM campaigns"

        if not include_archived:
            query += " WHERE status!='Archived'"

        query += " ORDER BY updated_at DESC, created_at DESC"
        return [self._campaign_row(row) for row in self.conn.execute(query).fetchall()]

    def delete_campaign(self, campaign_id):
        self.conn.execute("DELETE FROM campaign_run_items WHERE campaign_run_id IN (SELECT id FROM campaign_runs WHERE campaign_id=?)", (campaign_id,))
        self.conn.execute("DELETE FROM campaign_runs WHERE campaign_id=?", (campaign_id,))
        self.conn.execute("DELETE FROM campaign_targets WHERE campaign_id=?", (campaign_id,))
        self.conn.execute("DELETE FROM campaign_accounts WHERE campaign_id=?", (campaign_id,))
        self.conn.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
        self.conn.commit()

    def archive_campaign(self, campaign_id):
        return self.update_campaign(campaign_id, status="Archived")

    def duplicate_campaign(self, campaign_id):
        campaign = self.get_campaign(campaign_id)

        if not campaign:
            return None

        duplicate = self.create_campaign(
            name=f"{campaign['name']} Copy".strip(),
            description=campaign.get("description") or "",
            post_id=campaign.get("post_id"),
            delay_min_seconds=campaign.get("delay_min_seconds") or 0,
            delay_max_seconds=campaign.get("delay_max_seconds") or 0,
            stop_on_error=bool(campaign.get("stop_on_error")),
            stop_on_checkpoint=bool(campaign.get("stop_on_checkpoint")),
            continue_other_platforms_after_facebook_rate_limit=bool(
                campaign.get("continue_other_platforms_after_facebook_rate_limit")
            ),
            status="Draft",
        )
        accounts = self.get_campaign_accounts(campaign_id, enabled=None)
        targets = self.get_campaign_targets(campaign_id, enabled=None)
        self.replace_campaign_accounts(duplicate["id"], accounts)
        self.replace_campaign_targets(duplicate["id"], targets)
        return self.get_campaign(duplicate["id"])

    def replace_campaign_accounts(self, campaign_id, accounts):
        self.conn.execute("DELETE FROM campaign_accounts WHERE campaign_id=?", (campaign_id,))

        for account in accounts:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO campaign_accounts(campaign_id, platform, account_id, enabled)
                VALUES(?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    account["platform"],
                    int(account["account_id"]),
                    int(account.get("enabled", 1)),
                ),
            )

        self.conn.commit()

    def replace_campaign_targets(self, campaign_id, targets):
        self.conn.execute("DELETE FROM campaign_targets WHERE campaign_id=?", (campaign_id,))

        for target in targets:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO campaign_targets(campaign_id, platform, account_id, target_id, enabled)
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    target["platform"],
                    int(target["account_id"]),
                    int(target["target_id"]),
                    int(target.get("enabled", 1)),
                ),
            )

        self.conn.commit()

    def get_campaign_accounts(self, campaign_id, enabled=1):
        query = """
            SELECT
                campaign_accounts.*,
                accounts.name AS account_name,
                accounts.status AS account_status
            FROM campaign_accounts
            LEFT JOIN accounts ON accounts.id=campaign_accounts.account_id
            WHERE campaign_accounts.campaign_id=?
        """
        params = [campaign_id]

        if enabled is not None:
            query += " AND campaign_accounts.enabled=?"
            params.append(int(enabled))

        query += " ORDER BY campaign_accounts.platform, accounts.name"
        return [dict(row) for row in self.conn.execute(query, params).fetchall()]

    def get_campaign_targets(self, campaign_id, enabled=1):
        query = """
            SELECT *
            FROM campaign_targets
            WHERE campaign_id=?
        """
        params = [campaign_id]

        if enabled is not None:
            query += " AND enabled=?"
            params.append(int(enabled))

        query += " ORDER BY platform, account_id, target_id"
        return [dict(row) for row in self.conn.execute(query, params).fetchall()]

    def create_campaign_run(self, campaign_id, total_targets, message=""):
        cursor = self.conn.execute(
            """
            INSERT INTO campaign_runs(campaign_id, status, total_targets, started_at, message)
            VALUES(?, 'Running', ?, CURRENT_TIMESTAMP, ?)
            """,
            (campaign_id, int(total_targets or 0), message),
        )
        self.conn.commit()
        return self.get_campaign_run(cursor.lastrowid)

    def update_campaign_run(self, run_id, **fields):
        allowed = {
            "status",
            "processed_targets",
            "success_count",
            "failed_count",
            "skipped_count",
            "finished_at",
            "message",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}

        if not updates:
            return self.get_campaign_run(run_id)

        assignments = [f"{key}=?" for key in updates]
        values = list(updates.values())
        values.append(run_id)
        self.conn.execute(
            f"""
            UPDATE campaign_runs
            SET {", ".join(assignments)}
            WHERE id=?
            """,
            values,
        )
        self.conn.commit()
        return self.get_campaign_run(run_id)

    def get_campaign_run(self, run_id):
        row = self.conn.execute("SELECT * FROM campaign_runs WHERE id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def get_campaign_runs(self, campaign_id=None):
        query = """
            SELECT campaign_runs.*, campaigns.name AS campaign_name
            FROM campaign_runs
            LEFT JOIN campaigns ON campaigns.id=campaign_runs.campaign_id
            WHERE 1=1
        """
        params = []

        if campaign_id is not None:
            query += " AND campaign_runs.campaign_id=?"
            params.append(campaign_id)

        query += " ORDER BY campaign_runs.started_at DESC, campaign_runs.id DESC"
        return [dict(row) for row in self.conn.execute(query, params).fetchall()]

    def create_campaign_run_item(self, campaign_run_id, platform, account_id, target_id, post_id, status="Pending"):
        cursor = self.conn.execute(
            """
            INSERT INTO campaign_run_items(
                campaign_run_id,
                platform,
                account_id,
                target_id,
                post_id,
                status
            )
            VALUES(?, ?, ?, ?, ?, ?)
            """,
            (campaign_run_id, platform, int(account_id), int(target_id), int(post_id), status),
        )
        self.conn.commit()
        return self.get_campaign_run_item(cursor.lastrowid)

    def update_campaign_run_item(self, item_id, **fields):
        allowed = {
            "publish_history_id",
            "status",
            "message",
            "started_at",
            "finished_at",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}

        if not updates:
            return self.get_campaign_run_item(item_id)

        assignments = [f"{key}=?" for key in updates]
        values = list(updates.values())
        values.append(item_id)
        self.conn.execute(
            f"""
            UPDATE campaign_run_items
            SET {", ".join(assignments)}
            WHERE id=?
            """,
            values,
        )
        self.conn.commit()
        return self.get_campaign_run_item(item_id)

    def get_campaign_run_item(self, item_id):
        row = self.conn.execute("SELECT * FROM campaign_run_items WHERE id=?", (item_id,)).fetchone()
        return dict(row) if row else None

    def get_campaign_run_items(self, campaign_run_id):
        rows = self.conn.execute(
            """
            SELECT *
            FROM campaign_run_items
            WHERE campaign_run_id=?
            ORDER BY platform, account_id, target_id
            """,
            (campaign_run_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def campaign_stats(self):
        total = self.conn.execute("SELECT COUNT(*) FROM campaigns WHERE status!='Archived'").fetchone()[0]
        ready = self.conn.execute("SELECT COUNT(*) FROM campaigns WHERE status='Ready'").fetchone()[0]
        running = self.conn.execute("SELECT COUNT(*) FROM campaigns WHERE status IN ('Running', 'Stopping')").fetchone()[0]
        completed = self.conn.execute(
            "SELECT COUNT(*) FROM campaigns WHERE status IN ('Completed', 'CompletedWithErrors')"
        ).fetchone()[0]
        run_counts = self.conn.execute(
            """
            SELECT
                COALESCE(SUM(success_count), 0) AS success_count,
                COALESCE(SUM(failed_count), 0) AS failed_count,
                COALESCE(SUM(skipped_count), 0) AS skipped_count
            FROM campaign_runs
            WHERE status IN ('Completed', 'CompletedWithErrors', 'Stopped', 'Failed')
            """
        ).fetchone()
        attempts = run_counts["success_count"] + run_counts["failed_count"] + run_counts["skipped_count"]
        success_rate = round((run_counts["success_count"] / attempts) * 100, 1) if attempts else 0
        return {
            "total_campaigns": total,
            "ready_campaigns": ready,
            "running_campaigns": running,
            "completed_campaigns": completed,
            "campaign_success_rate": success_rate,
        }

    def _campaign_row(self, row):
        campaign = dict(row)
        for key in [
            "stop_on_error",
            "stop_on_checkpoint",
            "continue_other_platforms_after_facebook_rate_limit",
        ]:
            campaign[key] = bool(campaign.get(key))
        return campaign

    # =====================================================
    # TELEGRAM
    # =====================================================

    def add_telegram_account(self, name, bot_id, bot_username, secret_reference, status="Connected"):
        cursor = self.conn.execute(
            """
            INSERT INTO accounts(platform, name, profile_path, status, active, updated_at)
            VALUES('telegram', ?, '', ?, 1, CURRENT_TIMESTAMP)
            """,
            (name, status),
        )
        account_id = cursor.lastrowid
        self.conn.execute(
            """
            INSERT INTO telegram_accounts(
                account_id,
                bot_id,
                bot_username,
                encrypted_token_reference,
                status,
                last_checked,
                updated_at
            )
            VALUES(?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (account_id, str(bot_id), bot_username, secret_reference, status),
        )
        self.conn.commit()
        return self.get_telegram_account(account_id)

    def get_telegram_account(self, account_id):
        row = self.conn.execute(
            """
            SELECT
                accounts.id,
                accounts.platform,
                accounts.name,
                accounts.status,
                accounts.active,
                accounts.last_login,
                accounts.created_at,
                accounts.updated_at,
                telegram_accounts.bot_id,
                telegram_accounts.bot_username,
                telegram_accounts.encrypted_token_reference,
                telegram_accounts.last_checked
            FROM accounts
            JOIN telegram_accounts ON telegram_accounts.account_id=accounts.id
            WHERE accounts.id=?
            """,
            (account_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_telegram_accounts(self):
        rows = self.conn.execute(
            """
            SELECT
                accounts.id,
                accounts.platform,
                accounts.name,
                accounts.status,
                accounts.active,
                accounts.last_login,
                accounts.created_at,
                accounts.updated_at,
                telegram_accounts.bot_id,
                telegram_accounts.bot_username,
                telegram_accounts.encrypted_token_reference,
                telegram_accounts.last_checked
            FROM accounts
            JOIN telegram_accounts ON telegram_accounts.account_id=accounts.id
            WHERE accounts.platform='telegram'
            ORDER BY accounts.name
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def update_telegram_account_status(self, account_id, status, bot_username=None, bot_id=None):
        self.conn.execute(
            """
            UPDATE accounts
            SET status=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (status, account_id),
        )
        self.conn.execute(
            """
            UPDATE telegram_accounts
            SET status=?,
                bot_username=COALESCE(?, bot_username),
                bot_id=COALESCE(?, bot_id),
                last_checked=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            WHERE account_id=?
            """,
            (status, bot_username, str(bot_id) if bot_id is not None else None, account_id),
        )
        self.conn.commit()
        return self.get_telegram_account(account_id)

    def delete_telegram_account(self, account_id):
        self.conn.execute("DELETE FROM telegram_targets WHERE account_id=?", (account_id,))
        self.conn.execute("DELETE FROM telegram_accounts WHERE account_id=?", (account_id,))
        self.conn.execute("DELETE FROM accounts WHERE id=? AND platform='telegram'", (account_id,))
        self.conn.commit()

    def upsert_telegram_target(
        self,
        account_id,
        target_type,
        external_id,
        username="",
        name="",
        url="",
        selected=1,
        active=1,
        can_post=0,
        member_count=0,
        status="",
        metadata=None,
    ):
        metadata = metadata or {}
        self.conn.execute(
            """
            INSERT INTO telegram_targets(
                account_id,
                platform,
                target_type,
                external_id,
                username,
                name,
                url,
                selected,
                active,
                can_post,
                member_count,
                status,
                metadata,
                last_checked,
                updated_at
            )
            VALUES(?, 'telegram', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(account_id, external_id)
            DO UPDATE SET
                target_type=excluded.target_type,
                username=excluded.username,
                name=excluded.name,
                url=excluded.url,
                selected=excluded.selected,
                active=excluded.active,
                can_post=excluded.can_post,
                member_count=excluded.member_count,
                status=excluded.status,
                metadata=excluded.metadata,
                last_checked=CURRENT_TIMESTAMP,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                account_id,
                target_type,
                str(external_id),
                username,
                name,
                url,
                int(selected),
                int(active),
                int(can_post),
                int(member_count or 0),
                status,
                json.dumps(metadata) if not isinstance(metadata, str) else metadata,
            ),
        )
        self.conn.commit()
        return self.get_telegram_target_by_external_id(account_id, external_id)

    def get_telegram_targets(self, account_id=None, selected=None):
        query = "SELECT * FROM telegram_targets WHERE 1=1"
        params = []

        if account_id is not None:
            query += " AND account_id=?"
            params.append(account_id)

        if selected is not None:
            query += " AND selected=?"
            params.append(int(selected))

        query += " ORDER BY name"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def get_telegram_target(self, target_id):
        row = self.conn.execute(
            "SELECT * FROM telegram_targets WHERE id=?",
            (target_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_telegram_target_by_external_id(self, account_id, external_id):
        row = self.conn.execute(
            """
            SELECT *
            FROM telegram_targets
            WHERE account_id=? AND external_id=?
            """,
            (account_id, str(external_id)),
        ).fetchone()
        return dict(row) if row else None

    def set_telegram_target_selected(self, target_id, selected):
        self.conn.execute(
            """
            UPDATE telegram_targets
            SET selected=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (int(selected), target_id),
        )
        self.conn.commit()

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
        supported_platforms=None,
        platform_overrides=None,
        media_type="text",
        metadata=None,
    ):
        supported_platforms = supported_platforms or ["facebook"]
        platform_overrides = platform_overrides or {}
        metadata = metadata or {}
        cursor = self.conn.execute(
            """
            INSERT INTO posts(
                title,
                content,
                image_path,
                video_path,
                youtube_url,
                tags,
                supported_platforms,
                platform_overrides,
                media_type,
                metadata,
                status,
                updated_at
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                title,
                content,
                image_path,
                video_path,
                youtube_url,
                tags,
                json.dumps(supported_platforms),
                json.dumps(platform_overrides),
                media_type,
                json.dumps(metadata),
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
            "supported_platforms",
            "platform_overrides",
            "media_type",
            "metadata",
            "status",
        }
        updates = {
            key: value
            for key, value in fields.items()
            if key in allowed
        }

        for key in ["supported_platforms", "platform_overrides", "metadata"]:
            if key in updates and not isinstance(updates[key], str):
                updates[key] = json.dumps(updates[key])

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
            supported_platforms=json.loads(post.get("supported_platforms") or '["facebook"]'),
            platform_overrides=json.loads(post.get("platform_overrides") or "{}"),
            media_type=post.get("media_type") or "text",
            metadata=json.loads(post.get("metadata") or "{}"),
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

    def get_ready_posts(self):
        return self.get_posts(status="Ready")

    # =====================================================
    # HISTORY
    # =====================================================

    def add_publish_history(
        self,
        account_id,
        group_id,
        post_id,
        status,
        message="",
        started_at=None,
        finished_at=None,
        published_post_url="",
        campaign_id=None,
        platform="facebook",
        metadata=None,
    ):
        metadata = metadata or {}
        cursor = self.conn.execute(
            """
            INSERT INTO publish_history(
                account_id,
                group_id,
                post_id,
                status,
                message,
                started_at,
                finished_at,
                published_post_url,
                campaign_id,
                platform,
                metadata
            )
            VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                group_id,
                post_id,
                status,
                message,
                started_at,
                finished_at,
                published_post_url,
                campaign_id,
                platform,
                json.dumps(metadata) if not isinstance(metadata, str) else metadata,
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def update_publish_history(
        self,
        history_id,
        status,
        message="",
        finished_at=None,
        published_post_url="",
        metadata=None,
    ):
        metadata_value = None
        if metadata is not None:
            metadata_value = json.dumps(metadata) if not isinstance(metadata, str) else metadata

        self.conn.execute(
            """
            UPDATE publish_history
            SET status=?,
                message=?,
                finished_at=COALESCE(?, finished_at),
                published_post_url=COALESCE(NULLIF(?, ''), published_post_url),
                metadata=COALESCE(?, metadata)
            WHERE id=?
            """,
            (
                status,
                message,
                finished_at,
                published_post_url,
                metadata_value,
                history_id,
            ),
        )
        self.conn.commit()

    def get_publish_history(self, account_id=None, status=None, date=None, platform=None, campaign_id=None):
        query = """
            SELECT
                publish_history.*,
                accounts.name AS account_name,
                COALESCE(groups.name, telegram_targets.name) AS group_name,
                posts.title AS post_title,
                campaigns.name AS campaign_name
            FROM publish_history
            LEFT JOIN accounts ON accounts.id=publish_history.account_id
            LEFT JOIN groups ON groups.id=publish_history.group_id
            LEFT JOIN telegram_targets
                ON telegram_targets.id=publish_history.group_id
                AND publish_history.platform='telegram'
            LEFT JOIN posts ON posts.id=publish_history.post_id
            LEFT JOIN campaigns ON campaigns.id=publish_history.campaign_id
            WHERE 1=1
        """
        params = []

        if account_id and account_id != "All":
            query += " AND publish_history.account_id=?"
            params.append(account_id)

        if platform and platform != "All":
            query += " AND publish_history.platform=?"
            params.append(platform)

        if status and status != "All":
            query += " AND publish_history.status=?"
            params.append(status)

        if date:
            query += " AND DATE(COALESCE(publish_history.finished_at, publish_history.started_at, publish_history.created_at))=?"
            params.append(date)

        if campaign_id and campaign_id != "All":
            query += " AND publish_history.campaign_id=?"
            params.append(campaign_id)

        query += " ORDER BY COALESCE(publish_history.finished_at, publish_history.started_at, publish_history.created_at) DESC"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def count_publish_history(self, status=None, platform=None):
        terminal = [
            "Success",
            "Failed",
            "PermissionDenied",
            "Checkpoint",
            "Blocked",
            "Stopped",
            "InvalidToken",
            "ChatNotFound",
            "BotNotMember",
            "RateLimited",
            "NetworkError",
        ]
        query = (
            "SELECT COUNT(*) FROM publish_history "
            f"WHERE status IN ({','.join('?' for _ in terminal)})"
        )
        params = terminal

        if status:
            query += " AND status=?"
            params.append(status)

        if platform:
            query += " AND platform=?"
            params.append(platform)

        return self.conn.execute(query, params).fetchone()[0]

    def count_successful_publishes(self, platform=None):
        query = "SELECT COUNT(*) FROM publish_history WHERE status='Success'"
        params = []

        if platform:
            query += " AND platform=?"
            params.append(platform)

        return self.conn.execute(query, params).fetchone()[0]

    def count_failed_publishes(self, platform=None):
        query = """
            SELECT COUNT(*)
            FROM publish_history
            WHERE status IN ('Failed', 'PermissionDenied', 'Checkpoint', 'Blocked', 'InvalidToken', 'ChatNotFound', 'BotNotMember', 'RateLimited', 'NetworkError')
        """
        params = []

        if platform:
            query += " AND platform=?"
            params.append(platform)

        return self.conn.execute(query, params).fetchone()[0]

    def count_legacy_publish_history(self, status=None):
        query = "SELECT COUNT(*) FROM publish_history"
        params = ()

        if status:
            query += " WHERE status=?"
            params = (status,)

        return self.conn.execute(query, params).fetchone()[0]

    def publish_stats(self, platform=None):
        attempts = self.count_publish_history(platform=platform)
        successful = self.count_successful_publishes(platform=platform)
        failed = self.count_failed_publishes(platform=platform)
        success_rate = round((successful / attempts) * 100, 1) if attempts else 0

        return {
            "attempts": attempts,
            "successful": successful,
            "failed": failed,
            "success_rate": success_rate,
        }

    def add_history(
        self,
        group_id,
        status,
        message=""
    ):

        return self.add_publish_history(
            account_id=0,
            group_id=group_id,
            post_id=0,
            status=status,
            message=message,
        )

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
