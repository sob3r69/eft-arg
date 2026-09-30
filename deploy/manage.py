"""Build and manage the same production stack on macOS and Linux."""

import argparse
import os
from pathlib import Path
import secrets
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone

from dotenv import dotenv_values, set_key


ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / "deploy/.env"
RUNTIME = ROOT / ".runtime"
BIN = ROOT / "backend/.venv/bin"
CONF = ROOT / "deploy/supervisord.conf"


def run(*args, cwd=ROOT, **kwargs):
    return subprocess.run([str(arg) for arg in args], cwd=cwd, check=True, **kwargs)


def configure():
    if not ENV_FILE.exists():
        raise SystemExit("Run init first.")
    os.environ.update({k: v for k, v in dotenv_values(ENV_FILE).items() if v is not None})
    if os.environ.get("SECRET_KEY") in {None, "", "GENERATE_ON_INIT", "change-me"}:
        raise SystemExit("Set a unique SECRET_KEY in deploy/.env.")
    os.environ["APP_ROOT"] = str(ROOT)
    for variable, executable in (("NODE_BIN", "node"), ("CADDY_BIN", "caddy")):
        path = shutil.which(executable)
        if not path:
            raise SystemExit(f"Install {executable} and add it to PATH.")
        os.environ[variable] = path
    RUNTIME.mkdir(mode=0o700, exist_ok=True)


def control(*args, **kwargs):
    return run(BIN / "supervisorctl", "-c", CONF, *args, **kwargs)


def running():
    result = subprocess.run(
        [str(BIN / "supervisorctl"), "-c", str(CONF), "pid"],
        capture_output=True, text=True,
    )
    return result.returncode == 0 and result.stdout.strip().isdigit()


def stop():
    if running():
        pid = int(control("pid", capture_output=True, text=True).stdout.strip())
        control("shutdown")
        for _ in range(30):
            # The control socket closes before the children finish shutting down.
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(1)
        raise SystemExit("Shutdown timed out; inspect .runtime/*.log.")


def start(foreground=False):
    if running():
        control("status")
        return
    if not (ROOT / "frontend/.output/server/index.mjs").exists():
        raise SystemExit("Run build first.")
    for port in (3000, 8000):
        with socket.socket() as probe:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                raise SystemExit(f"Port {port} is occupied; stop the other server first.")
    run(os.environ["CADDY_BIN"], "validate", "--config", ROOT / "deploy/Caddyfile")
    args = [str(BIN / "supervisord"), "-c", str(CONF)]
    if foreground:
        os.execv(args[0], [*args, "-n"])
    run(*args)
    time.sleep(3)
    control("status")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "allow-host", "build", "start", "run", "stop", "restart", "status"])
    parser.add_argument("host", nargs="?")
    args = parser.parse_args()

    if args.command == "init":
        if not ENV_FILE.exists():
            with ENV_FILE.open("x") as target:
                target.write((ROOT / "deploy/.env.example").read_text().replace("GENERATE_ON_INIT", secrets.token_urlsafe(48)))
            ENV_FILE.chmod(0o600)
        print("Configuration: deploy/.env")
        return

    configure()
    if args.command == "allow-host":
        if not args.host or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-" for c in args.host):
            raise SystemExit("Pass an IPv4 address or DNS hostname, without protocol or port.")
        hosts = os.environ["ALLOWED_HOSTS"].split(",")
        if args.host not in hosts:
            set_key(str(ENV_FILE), "ALLOWED_HOSTS", ",".join([*hosts, args.host]))
        print("Host added. Run restart to apply.")
    elif args.command == "build":
        if running():
            raise SystemExit("Stop the stack before rebuilding: deploy/manage.py stop")
        # SQLite's backup API also includes committed data from a WAL file.
        database = ROOT / "backend/db.sqlite3"
        if database.exists():
            backups = RUNTIME / "backups"
            backups.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            with sqlite3.connect(database) as source, sqlite3.connect(backups / f"db-{stamp}.sqlite3") as target:
                source.backup(target)
        run("npm", "ci", cwd=ROOT / "frontend")
        run("npm", "run", "build", cwd=ROOT / "frontend", env={**os.environ, "VITE_API_BASE_URL": "/api"})
        run(BIN / "python", "manage.py", "check", cwd=ROOT / "backend")
        run(BIN / "python", "manage.py", "migrate", "--noinput", cwd=ROOT / "backend")
        run(BIN / "python", "manage.py", "collectstatic", "--noinput", cwd=ROOT / "backend")
    elif args.command == "stop":
        stop()
    elif args.command == "restart":
        stop()
        start()
    elif args.command == "status":
        control("status")
    else:
        start(foreground=args.command == "run")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
