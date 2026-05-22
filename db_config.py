"""Centralized database configuration.

All database credentials are read from environment variables. For local
development, place them in a .env file (see .env.example) — the .env file is
git-ignored and must never be committed. Production (Railway) injects these
as service variables automatically.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv is optional — environment variables may be set directly.
    pass

# Public Railway proxy host, used as a connection fallback.
PUBLIC_PROXY_HOST = "yamabiko.proxy.rlwy.net"

DB_HOST = os.environ.get("DB_HOST", PUBLIC_PROXY_HOST)
DB_NAME = os.environ.get("DB_NAME", "railway")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PORT = os.environ.get("DB_PORT", "27535")
DB_PASS = os.environ.get("DB_PASS")

if not DB_PASS:
    raise RuntimeError(
        "DB_PASS environment variable is not set. Database credentials must be "
        "supplied via the environment — a local .env file or Railway service "
        "variables. See .env.example for the full list of required variables."
    )
