"""Container entrypoint for the preview role."""

import os

import uvicorn

from moyu_config import ConfigProvider
from moyu_storage import Storage

from .service import create_preview_app


def required(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"缺少环境变量 {name}")
    return value


def main():
    provider = ConfigProvider(required("MOYU_CONFIG_DIR"), read_only=True)
    effective = provider.load()
    storage = Storage(effective.modules["storage"]["dataRoot"]).ensure_layout()
    app = create_preview_app(storage, effective.modules["preview"])
    listen = required("MOYU_PREVIEW_LISTEN")
    if ":" not in listen:
        raise SystemExit("MOYU_PREVIEW_LISTEN 必须形如 host:port")
    host, port = listen.rsplit(":", 1)
    uvicorn.run(app, host=host, port=int(port), log_level="info")


if __name__ == "__main__":
    main()
