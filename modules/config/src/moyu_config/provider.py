"""Config directory loader and writer.

Layout (relative to the configured config directory)::

    moyu.yaml
    modules/{gateway,api,worker,preview,storage,uploads}.yaml
    state/last-known-good/
    state/backups/

Runtime configuration is file-based. Secrets live outside these files and are
never written by this module.
"""

import copy
import datetime as dt
import hashlib
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema
import yaml

from .defaults import SCHEMA_FILES, default_for, file_for
from .errors import ConfigError
from .migrations import CURRENT_VERSION, MIGRATIONS, migration_for

STATE_DIR = "state"
LKG_DIR = "last-known-good"
BACKUPS_DIR = "backups"
CONFIG_NAMES = ("global", "gateway", "api", "worker", "preview", "storage", "uploads")


@dataclass
class EffectiveConfig:
    global_config: dict
    modules: dict
    revisions: dict
    degraded: tuple = field(default_factory=tuple)

    def get(self, name):
        return self.global_config if name == "global" else self.modules[name]

    def to_dict(self):
        return {
            "global": copy.deepcopy(self.global_config),
            "modules": copy.deepcopy(self.modules),
            "revisions": dict(self.revisions),
            "degraded": list(self.degraded),
        }


@dataclass
class WriteResult:
    name: str
    revision: str
    data: dict
    backup: str


def _deep_merge(base, patch):
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        elif isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


class ConfigProvider:
    def __init__(
        self,
        config_dir,
        schemas_dir=None,
        read_only=False,
        migrations=None,
        current_version=CURRENT_VERSION,
    ):
        self.config_dir = Path(config_dir)
        self.read_only = bool(read_only)
        self.migrations = MIGRATIONS if migrations is None else migrations
        self.current_version = int(current_version)
        self.state_dir = self.config_dir / STATE_DIR
        self.lkg_dir = self.state_dir / LKG_DIR
        self.backup_dir = self.state_dir / BACKUPS_DIR
        self.audit_path = self.state_dir / "audit.db"
        default_schemas = Path(__file__).resolve().parents[2] / "schemas"
        self.schemas_dir = Path(schemas_dir) if schemas_dir else default_schemas
        self._validators = {}

    def ensure_layout(self):
        if self.read_only:
            if not self.config_dir.is_dir():
                raise ConfigError("config_missing", f"配置目录不存在: {self.config_dir}")
            return
        try:
            for directory in (
                self.config_dir,
                self.config_dir / "modules",
                self.state_dir,
                self.lkg_dir,
                self.backup_dir,
            ):
                directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConfigError("config_unwritable", f"无法创建配置目录: {exc}") from exc

    def _path_for(self, name):
        return self.config_dir / file_for(name)

    def _lkg_path(self, name):
        return self.lkg_dir / file_for(name).replace("/", "-")

    def _schema(self, name):
        path = self.schemas_dir / SCHEMA_FILES[name]
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise ConfigError("schema_missing", f"无法读取 schema {path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ConfigError("schema_invalid", f"schema 不是合法 JSON {path}: {exc}") from exc

    def _validator(self, name):
        if name not in self._validators:
            schema = self._schema(name)
            try:
                jsonschema.Draft202012Validator.check_schema(schema)
            except jsonschema.SchemaError as exc:
                raise ConfigError("schema_invalid", f"schema 非法 {name}: {exc.message}") from exc
            self._validators[name] = jsonschema.Draft202012Validator(schema)
        return self._validators[name]

    def validate(self, name, data):
        if name not in CONFIG_NAMES:
            raise ConfigError("unknown_config", f"未知配置: {name}")
        validator = self._validator(name)
        errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
        if errors:
            details = []
            for error in errors:
                path = ".".join(str(part) for part in error.path) or "<root>"
                details.append(f"{path}: {error.message}")
            raise ConfigError("schema_invalid", f"{name} 配置不合法", details)
        return data

    def _parse(self, text, name):
        try:
            for event in yaml.parse(text):
                if isinstance(event, yaml.events.AliasEvent) or getattr(
                    event, "anchor", None
                ):
                    raise ConfigError(
                        "yaml_alias", f"{name}: 禁止 YAML anchor/alias"
                    )
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ConfigError("yaml_invalid", f"{name}: YAML 解析失败: {exc}") from exc
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise ConfigError("yaml_invalid", f"{name}: 顶层必须是映射")
        if "<<" in data:
            raise ConfigError("yaml_alias", f"{name}: 禁止 YAML merge key")
        return data

    def _atomic_write(self, path, data, mode=0o640):
        path.parent.mkdir(parents=True, exist_ok=True)
        text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
        fd, tmp = tempfile.mkstemp(prefix=".moyu-config-", suffix=".part", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp, mode)
            os.replace(tmp, path)
            tmp = None
        except OSError as exc:
            raise ConfigError("config_write_failed", f"写入配置失败 {path}: {exc}") from exc
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def _revision(self, path):
        try:
            return _sha256_bytes(path.read_bytes())
        except OSError as exc:
            raise ConfigError("config_unreadable", f"无法读取 {path}: {exc}") from exc

    def _read_valid(self, path, name):
        text = path.read_text(encoding="utf-8")
        data = self._parse(text, name)
        version = int(data.get("schemaVersion", 1))
        if version > self.current_version:
            raise ConfigError(
                "schema_newer",
                f"{name}: schemaVersion {version} 高于当前支持的 {self.current_version}",
            )
        if version < self.current_version:
            raise ConfigError(
                "migration_required",
                f"{name}: schemaVersion {version} 需要迁移到 {self.current_version}",
            )
        return self.validate(name, data)

    def _maybe_migrate(self, path, name):
        text = path.read_text(encoding="utf-8")
        data = self._parse(text, name)
        version = int(data.get("schemaVersion", 1))
        if version > self.current_version:
            raise ConfigError(
                "schema_newer",
                f"{name}: schemaVersion {version} 高于当前支持的 {self.current_version}",
            )
        if version == self.current_version:
            return
        if self.read_only:
            raise ConfigError(
                "migration_required",
                f"{name}: schemaVersion {version} 需要在可写模式迁移到 {self.current_version}",
            )
        original = version
        before = self._revision(path)
        backup = self._backup(name, path, before, f"pre-migrate-v{version}")
        steps = []
        while version < self.current_version:
            migration = migration_for(self.migrations, name, version)
            if migration is None:
                raise ConfigError(
                    "migration_missing",
                    f"{name}: 缺少 {version} -> {version + 1} 的迁移",
                )
            data = migration.apply(copy.deepcopy(data)) or {}
            version = migration.to_version
            data["schemaVersion"] = version
            steps.append(
                migration.description or f"{migration.from_version}->{migration.to_version}"
            )
        self.validate(name, data)
        self._atomic_write(path, data)
        self._record_audit(
            "system",
            name,
            "migrate",
            before,
            self._revision(path),
            "ok",
            {
                "from": original,
                "to": version,
                "backup": str(backup),
                "migrations": steps,
            },
        )

    def _read_lkg(self, name):
        path = self._lkg_path(name)
        if not path.exists():
            return None
        try:
            data = self._read_valid(path, name)
        except (ConfigError, OSError):
            return None
        return data

    def _snapshot_lkg(self, name, data):
        self._atomic_write(self._lkg_path(name), data)

    def load(self):
        self.ensure_layout()
        global_config = None
        modules = {}
        revisions = {}
        degraded = []

        for name in CONFIG_NAMES:
            path = self._path_for(name)
            if not path.exists():
                data = default_for(name)
                data["schemaVersion"] = self.current_version
                self.validate(name, data)
                if not self.read_only:
                    self._atomic_write(path, data)
            else:
                try:
                    self._maybe_migrate(path, name)
                    data = self._read_valid(path, name)
                except ConfigError as exc:
                    if exc.code in (
                        "schema_newer",
                        "migration_missing",
                        "migration_required",
                    ):
                        raise
                    fallback = self._read_lkg(name)
                    if fallback is None:
                        raise ConfigError(
                            exc.code,
                            f"{name}: 配置非法且没有 last-known-good: {exc.message}",
                            exc.details,
                        ) from exc
                    data = fallback
                    degraded.append(name)
            if path.exists():
                revisions[name] = self._revision(path)
            else:
                revisions[name] = _sha256_bytes(
                    json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
                )
            if not self.read_only:
                self._snapshot_lkg(name, data)
            if name == "global":
                global_config = data
            else:
                modules[name] = data

        return EffectiveConfig(
            global_config=global_config,
            modules=modules,
            revisions=revisions,
            degraded=tuple(degraded),
        )

    def write(self, name, patch, revision=None, actor="api"):
        if self.read_only:
            raise ConfigError("read_only", "配置以只读方式加载，不能写入")
        if name not in CONFIG_NAMES:
            raise ConfigError("unknown_config", f"未知配置: {name}")
        if not isinstance(patch, dict):
            raise ConfigError("invalid_patch", "patch 必须是映射")
        self.ensure_layout()
        path = self._path_for(name)
        if not path.exists():
            current = default_for(name)
            current["schemaVersion"] = self.current_version
            self.validate(name, current)
            self._atomic_write(path, current)
        current_revision = self._revision(path)
        if revision is not None and revision != current_revision:
            raise ConfigError(
                "revision_conflict",
                f"{name}: 配置已被其他人修改",
                [f"expected={revision}", f"actual={current_revision}"],
            )
        current = self._read_valid(path, name)
        merged = _deep_merge(current, patch)
        self.validate(name, merged)
        backup = self._backup(name, path, current_revision)
        self._atomic_write(path, merged)
        self._snapshot_lkg(name, merged)
        new_revision = self._revision(path)
        self._record_audit(
            actor,
            name,
            "write",
            current_revision,
            new_revision,
            "ok",
            {"backup": str(backup)},
        )
        return WriteResult(
            name=name,
            revision=new_revision,
            data=merged,
            backup=str(backup),
        )

    def _backup_path(self, name, revision, suffix=""):
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        tail = f"-{suffix}" if suffix else ""
        return self.backup_dir / f"{name}-{stamp}-{revision[:12]}{tail}.yaml"

    def _backup(self, name, path, revision, suffix=""):
        target = self._backup_path(name, revision, suffix)
        try:
            target.write_bytes(path.read_bytes())
        except OSError as exc:
            raise ConfigError("backup_failed", f"备份 {name} 失败: {exc}") from exc
        return target

    def _audit_connection(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.audit_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS config_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                actor TEXT NOT NULL,
                module TEXT NOT NULL,
                action TEXT NOT NULL,
                revision_before TEXT NOT NULL,
                revision_after TEXT NOT NULL,
                result TEXT NOT NULL,
                details TEXT NOT NULL
            )
            """
        )
        return connection

    def _record_audit(
        self, actor, module, action, revision_before, revision_after, result, details
    ):
        if self.read_only:
            return
        try:
            connection = self._audit_connection()
            with connection:
                connection.execute(
                    "INSERT INTO config_audit"
                    " (created_at, actor, module, action, revision_before, revision_after, result, details)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        dt.datetime.now(dt.timezone.utc).isoformat(),
                        str(actor),
                        module,
                        action,
                        revision_before or "",
                        revision_after or "",
                        result,
                        json.dumps(details or {}, ensure_ascii=False),
                    ),
                )
            connection.close()
        except sqlite3.Error as exc:
            raise ConfigError("audit_failed", f"写入配置审计失败: {exc}") from exc

    def audit(self, limit=100):
        if not self.audit_path.exists():
            return []
        connection = self._audit_connection()
        try:
            rows = connection.execute(
                "SELECT * FROM config_audit ORDER BY id DESC LIMIT ?", (int(limit),)
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "actor": row["actor"],
                "module": row["module"],
                "action": row["action"],
                "revision_before": row["revision_before"],
                "revision_after": row["revision_after"],
                "result": row["result"],
                "details": json.loads(row["details"]),
            }
            for row in rows
        ]

    def last_known_good(self, name):
        if name not in CONFIG_NAMES:
            raise ConfigError("unknown_config", f"未知配置: {name}")
        data = self._read_lkg(name)
        if data is None:
            raise ConfigError("lkg_missing", f"{name}: 没有 last-known-good")
        return data