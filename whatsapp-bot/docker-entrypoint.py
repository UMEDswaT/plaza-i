"""Start service with persistent database ownership and a nonroot worker."""
import os
import pwd
import sys
from pathlib import Path

port = int(os.environ.get('PORT', '8000'))
if not 1 <= port <= 65535:
    raise RuntimeError('Invalid PORT')
p = Path(os.environ.get('DATABASE_PATH', '/app/data/plazai.sqlite3')).parent
p.mkdir(parents=True, exist_ok=True)
if os.geteuid() == 0:
    u = pwd.getpwnam('bot')
    os.chown(p, u.pw_uid, u.pw_gid)
    for suffix in ('', '-wal', '-shm'):
        f = Path(os.environ.get('DATABASE_PATH', '/app/data/plazai.sqlite3') + suffix)
        if f.exists(): os.chown(f, u.pw_uid, u.pw_gid)
    os.setgroups([])
    os.setgid(u.pw_gid)
    os.setuid(u.pw_uid)
os.execv(sys.executable, [sys.executable,'-m','uvicorn','app.main:app','--host','0.0.0.0','--port',str(port),'--workers','1','--proxy-headers'])
