"""Configuration schema migrations.

v0.0.1 starts at schemaVersion 1, so the registry is empty. The framework is
exercised by tests with injected migrations (1 -> 2) and is ready for future
versions.
"""

from dataclasses import dataclass
from typing import Callable

CURRENT_VERSION = 1


@dataclass(frozen=True)
class Migration:
    module: str
    from_version: int
    to_version: int
    apply: Callable[[dict], dict]
    description: str = ""


MIGRATIONS: dict = {}


def migration_for(registry, module, from_version):
    migration = registry.get((module, from_version))
    if migration is None:
        return None
    if migration.to_version != from_version + 1:
        raise ValueError(
            f"{module}: 迁移必须逐版本递增，"
            f"{migration.from_version} -> {migration.to_version}"
        )
    return migration
