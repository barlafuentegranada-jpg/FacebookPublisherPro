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

            url TEXT UNIQUE,

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

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    # GROUPS
    # =====================================================

    def save_group(
        self,
        account_id,
        name,
        url,
        members=""
    ):

        self.conn.execute(
            """
            INSERT OR REPLACE INTO groups
            (
                account_id,
                name,
                url,
                members,
                selected,
                last_scan
            )
            VALUES
            (
                ?,
                ?,
                ?,
                ?,
                1,
                CURRENT_TIMESTAMP
            )
            """,
            (
                account_id,
                name,
                url,
                members
            )
        )

        self.conn.commit()

    # =====================================================

    def get_groups(self):

        cur = self.conn.execute(
            """
            SELECT *
            FROM groups
            ORDER BY name
            """
        )

        return cur.fetchall()

    # =====================================================

    def get_selected_groups(self):

        cur = self.conn.execute(
            """
            SELECT *
            FROM groups
            WHERE selected=1
            ORDER BY name
            """
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
            category=?
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