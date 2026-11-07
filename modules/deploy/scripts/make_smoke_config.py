#!/usr/bin/env python3
"""Generate a self-contained config tree for the Podman smoke test."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "modules" / "config" / "src"))

from moyu_config import ConfigProvider  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("config_dir")
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--cache-dir", required=True)
    parser.add_argument("--web-root", required=True)
    parser.add_argument("--upstream", required=True)
    parser.add_argument("--gateway-port", type=int, required=True)
    parser.add_argument("--cert-dir", required=True)
    parser.add_argument("--admin-port", type=int, default=9443)
    parser.add_argument("--preview-url", default="")
    args = parser.parse_args()

    provider = ConfigProvider(args.config_dir)
    effective = provider.load()
    provider.write(
        "storage",
        {"dataRoot": args.data_root},
        revision=effective.revisions["storage"],
    )
    preview_patch = {"cacheDir": args.cache_dir}
    if args.preview_url:
        preview_patch["serviceUrl"] = args.preview_url
    provider.write(
        "preview", preview_patch, revision=effective.revisions["preview"]
    )
    provider.write(
        "api", {"webRoot": args.web_root}, revision=effective.revisions["api"]
    )
    provider.write(
        "gateway",
        {
            "enabled": True,
            "listen": {"ipv4": "0.0.0.0", "ipv6": "", "port": args.gateway_port},
            "cert": {
                "certFile": f"{args.cert_dir}/tls.crt",
                "keyFile": f"{args.cert_dir}/tls.key",
            },
            "reload": {
                "onStart": True,
                "pollInterval": "0s",
                "watch": False,
                "signal": False,
                "api": {
                    "enabled": True,
                    "listen": f"127.0.0.1:{args.admin_port}",
                    "tokenFile": "/config/secrets/gateway_reload_token",
                },
            },
            "upstream": {"url": args.upstream},
        },
        revision=effective.revisions["gateway"],
    )
    print("config ready")


if __name__ == "__main__":
    main()
