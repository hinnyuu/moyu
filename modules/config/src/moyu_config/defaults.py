"""Built-in defaults for every configuration file.

Values here are defaults, not fixed deployment facts. Ports and paths are
examples that the operator can change in ``/config``; no runtime module reads
them from this file directly.
"""

import copy

GLOBAL_FILE = "moyu.yaml"
MODULE_FILES = {
    "gateway": "modules/gateway.yaml",
    "api": "modules/api.yaml",
    "worker": "modules/worker.yaml",
    "preview": "modules/preview.yaml",
    "storage": "modules/storage.yaml",
    "uploads": "modules/uploads.yaml",
}

SCHEMA_FILES = {
    "global": "moyu.schema.json",
    "gateway": "gateway.schema.json",
    "api": "api.schema.json",
    "worker": "worker.schema.json",
    "preview": "preview.schema.json",
    "storage": "storage.schema.json",
    "uploads": "uploads.schema.json",
}

DEFAULTS = {
    "global": {
        "schemaVersion": 1,
        "timezone": "UTC",
        "modules": {
            "gateway": False,
            "api": True,
            "worker": True,
            "preview": True,
            "storage": True,
            "uploads": True,
        },
    },
    "gateway": {
        "schemaVersion": 1,
        "enabled": False,
        "listen": {"ipv4": "0.0.0.0", "ipv6": "::", "port": 8443},
        "cert": {
            "certFile": "/certs/tls.crt",
            "keyFile": "/certs/tls.key",
        },
        "reload": {
            "onStart": True,
            "pollInterval": "30s",
            "watch": False,
            "signal": False,
            "api": {
                "enabled": True,
                "listen": "127.0.0.1:9443",
                "tokenFile": "/config/secrets/gateway_reload_token",
            },
        },
        "upstream": {"url": "http://api"},
    },
    "api": {
        "schemaVersion": 1,
        "session": {"cookieName": "moyu_session", "ttlSeconds": 86400},
        "maxJsonBodyBytes": 1048576,
        "webRoot": "/app/web",
    },
    "worker": {
        "schemaVersion": 1,
        "concurrency": 1,
        "jobTimeoutSeconds": 3600,
        "pollIntervalSeconds": 2,
    },
    "preview": {
        "schemaVersion": 1,
        "enabled": True,
        "cacheDir": "/data/preview",
        "concurrency": 2,
        "maxMemoryBytes": 268435456,
        "timeoutSeconds": 60,
    },
    "storage": {
        "schemaVersion": 1,
        "dataRoot": "/data",
        "quotaBytes": 0,
        "uploadTtlSeconds": 86400,
        "previewTtlSeconds": 604800,
    },
    "uploads": {
        "schemaVersion": 1,
        "maxUploadBytes": 2147483648,
        "sessionTtlSeconds": 86400,
        "chunkSizeBytes": 8388608,
        "tusBasePath": "/files",
    },
}


def default_for(name):
    try:
        return copy.deepcopy(DEFAULTS[name])
    except KeyError as exc:
        raise KeyError(f"未知配置: {name}") from exc


def file_for(name):
    if name == "global":
        return GLOBAL_FILE
    return MODULE_FILES[name]


def schema_for(name):
    return SCHEMA_FILES[name]