"""Container entrypoint for the API role.

Only bootstrap/deployment facts come from environment variables. Runtime
configuration is loaded from ``MOYU_CONFIG_DIR``.
"""

import os

import uvicorn

from moyu_config import ConfigProvider
from moyu_storage import Storage

from . import AuthManager, create_app


def required(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"缺少环境变量 {name}")
    return value


def main():
    config_dir = required("MOYU_CONFIG_DIR")
    provider = ConfigProvider(config_dir)
    effective = provider.load()
    storage_config = effective.modules["storage"]
    storage = Storage(
        storage_config["dataRoot"],
        quota_bytes=storage_config.get("quotaBytes", 0),
    ).ensure_layout()

    api_config = effective.modules["api"]
    auth = AuthManager(
        bootstrap_token_file=required("MOYU_BOOTSTRAP_TOKEN_FILE"),
        state_file=required("MOYU_SESSION_STATE_FILE"),
        secret_file=required("MOYU_SESSION_SECRET_FILE"),
        cookie_name=api_config["session"]["cookieName"],
        ttl_seconds=api_config["session"]["ttlSeconds"],
        cookie_secure=os.environ.get("MOYU_COOKIE_SECURE") == "1",
    )
    app = create_app(
        storage,
        provider,
        auth,
        tusd_hook_token=os.environ.get("MOYU_TUSD_HOOK_TOKEN", ""),
    )

    listen = os.environ.get("MOYU_API_LISTEN", "")
    if ":" not in listen:
        raise SystemExit("MOYU_API_LISTEN 必须形如 host:port")
    host, port = listen.rsplit(":", 1)
    uvicorn.run(app, host=host, port=int(port), log_level="info")


if __name__ == "__main__":
    main()