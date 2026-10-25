"""SQLite-backed queue and conversations. Designed for ONE app instance."""
import os
import sqlite3
import time
from contextlib import contextmanager


class Storage:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with self.db() as conn:
            conn.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS contacts (
                    wa_id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL DEFAULT 'ai' CHECK(mode IN ('ai','human')),
                    updated REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wa_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user','assistant','staff')),
                    body TEXT NOT NULL,
                    created REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS messages_contact ON messages(wa_id,id);
                CREATE TABLE IF NOT EXISTS queue (
                    meta_id TEXT PRIMARY KEY,
                    wa_id TEXT NOT NULL,
                    msg_seq INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    ready_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS queue_pending ON queue(status,ready_at);
            """)

    @contextmanager
    def db(self):
        con = sqlite3.connect(self.path, timeout=20)
        con.row_factory = sqlite3.Row
        try:
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    def receive(self, msg_id: str, wa_id: str, body: str) -> bool:
        now = time.time()
        with self.db() as con:
            con.execute("BEGIN IMMEDIATE")
            if con.execute("SELECT 1 FROM queue WHERE meta_id=?", (msg_id,)).fetchone():
                return False
            con.execute("INSERT OR IGNORE INTO contacts(wa_id,updated) VALUES(?,?)", (wa_id, now))
            con.execute("UPDATE contacts SET updated=? WHERE wa_id=?", (now, wa_id))
            c = con.execute("INSERT INTO messages(wa_id,role,body,created) VALUES(?,'user',?,?)", (wa_id,body,now))
            con.execute("INSERT INTO queue(meta_id,wa_id,msg_seq,status,ready_at) VALUES(?,?,?,'pending',?)", (msg_id,wa_id,c.lastrowid,now))
            return True

    def claim(self):
        with self.db() as con:
            con.execute("BEGIN IMMEDIATE")
            record = con.execute("SELECT * FROM queue WHERE status='pending' AND ready_at<=? ORDER BY msg_seq LIMIT 1", (time.time(),)).fetchone()
            if not record:
                return None
            con.execute("UPDATE queue SET status='working',attempts=attempts+1 WHERE meta_id=?", (record['meta_id'],))
            return dict(record)

    def finish(self, msg_id: str):
        with self.db() as con:
            con.execute("UPDATE queue SET status='done' WHERE meta_id=?", (msg_id,))

    def retry(self, msg_id: str):
        with self.db() as con:
            row=con.execute("SELECT attempts FROM queue WHERE meta_id=?",(msg_id,)).fetchone()
            if not row:
                return False
            attempts = row['attempts']
            if attempts >= 5:
                con.execute("UPDATE queue SET status='failed' WHERE meta_id=?", (msg_id,))
                return True
            con.execute("UPDATE queue SET status='pending',ready_at=? WHERE meta_id=?", (time.time() + min(120,2**attempts), msg_id))
            return False

    def recover(self):
        # If the process crashed, unfinished events may be retried. Meta may have accepted a send already.
        with self.db() as con:
            con.execute("UPDATE queue SET status='pending',ready_at=? WHERE status='working'",(time.time(),))

    def mode(self, wa_id: str):
        with self.db() as con:
            row=con.execute("SELECT mode FROM contacts WHERE wa_id=?",(wa_id,)).fetchone()
            return row['mode'] if row else 'ai'

    def set_mode(self, wa_id: str, mode: str):
        if mode not in ('ai','human'):
            raise ValueError('Invalid mode')
        with self.db() as con:
            now=time.time()
            con.execute("INSERT INTO contacts(wa_id,mode,updated) VALUES(?,?,?) ON CONFLICT(wa_id) DO UPDATE SET mode=excluded.mode,updated=excluded.updated",(wa_id,mode,now))

    def transcript(self, wa_id: str, through: int | None = None, limit=16):
        with self.db() as con:
            if through is None:
                records=con.execute("SELECT role,body FROM messages WHERE wa_id=? ORDER BY id DESC LIMIT ?",(wa_id,limit)).fetchall()
            else:
                records=con.execute("SELECT role,body FROM messages WHERE wa_id=? AND id<=? ORDER BY id DESC LIMIT ?",(wa_id,through,limit)).fetchall()
            return [dict(x) for x in reversed(records)]

    def append(self, wa_id: str, role: str, body: str):
        with self.db() as con:
            con.execute("INSERT INTO messages(wa_id,role,body,created) VALUES(?,?,?,?)",(wa_id,role,body,time.time()))
            con.execute("UPDATE contacts SET updated=? WHERE wa_id=?",(time.time(),wa_id))

    def list_chats(self, limit=100):
        with self.db() as con:
            rows=con.execute("""SELECT c.wa_id,c.mode,c.updated,COALESCE((SELECT body FROM messages WHERE wa_id=c.wa_id ORDER BY id DESC LIMIT 1),'') AS last_message FROM contacts c ORDER BY c.updated DESC LIMIT ?""",(limit,)).fetchall()
            return [dict(x) for x in rows]

    def chat_details(self, wa_id: str):
        with self.db() as con:
            rows=con.execute("SELECT role,body,created FROM messages WHERE wa_id=? ORDER BY id DESC LIMIT 100",(wa_id,)).fetchall()
            return [dict(x) for x in reversed(rows)]

    def delete_chat(self, wa_id: str):
        with self.db() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("DELETE FROM queue WHERE wa_id=?", (wa_id,))
            con.execute("DELETE FROM messages WHERE wa_id=?", (wa_id,))
            con.execute("DELETE FROM contacts WHERE wa_id=?", (wa_id,))
