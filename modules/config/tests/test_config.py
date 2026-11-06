import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "modules" / "config" / "src"))

from moyu_config import (  # noqa: E402
    DEFAULTS,
    ConfigError,
    ConfigProvider,
    default_for,
)


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "config"
        self.provider = ConfigProvider(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_creates_defaults_and_lkg(self):
        effective = self.provider.load()
        self.assertEqual(effective.global_config, DEFAULTS["global"])
        self.assertEqual(effective.modules["worker"], DEFAULTS["worker"])
        self.assertEqual(effective.degraded, ())
        self.assertEqual(
            (self.root / "moyu.yaml").exists(),
            True,
        )
        for name in DEFAULTS:
            self.assertIn(name, effective.revisions)
            self.assertTrue((self.root / "state" / "last-known-good").exists())
        self.assertTrue((self.root / "modules" / "gateway.yaml").exists())
        self.assertTrue((self.root / "modules" / "api.yaml").exists())

    def test_unknown_field_falls_back_to_lkg(self):
        self.provider.load()
        api_path = self.root / "modules" / "api.yaml"
        data = yaml.safe_load(api_path.read_text(encoding="utf-8"))
        data["unexpected"] = True
        api_path.write_text(yaml.safe_dump(data), encoding="utf-8")

        effective = self.provider.load()
        self.assertIn("api", effective.degraded)
        self.assertEqual(effective.modules["api"], DEFAULTS["api"])

    def test_invalid_without_lkg_raises(self):
        (self.root / "modules").mkdir(parents=True)
        (self.root / "modules" / "api.yaml").write_text(
            "schemaVersion: 1\nunexpected: true\n", encoding="utf-8"
        )
        with self.assertRaises(ConfigError) as ctx:
            self.provider.load()
        self.assertEqual(ctx.exception.code, "schema_invalid")

    def test_yaml_alias_rejected(self):
        (self.root / "modules").mkdir(parents=True)
        (self.root / "modules" / "api.yaml").write_text(
            """
schemaVersion: 1
session: &session
  cookieName: sid
  ttlSeconds: 60
maxJsonBodyBytes: 1024
copy: *session
""",
            encoding="utf-8",
        )
        with self.assertRaises(ConfigError) as ctx:
            self.provider.load()
        self.assertEqual(ctx.exception.code, "yaml_alias")

    def test_write_revision_and_validation(self):
        effective = self.provider.load()
        revision = effective.revisions["worker"]
        result = self.provider.write("worker", {"concurrency": 4}, revision=revision)
        self.assertEqual(result.data["concurrency"], 4)
        self.assertNotEqual(result.revision, revision)
        self.assertTrue(Path(result.backup).exists())

        reloaded = self.provider.load()
        self.assertEqual(reloaded.modules["worker"]["concurrency"], 4)
        self.assertEqual(self.provider.last_known_good("worker")["concurrency"], 4)

        with self.assertRaises(ConfigError) as ctx:
            self.provider.write("worker", {"concurrency": 5}, revision=revision)
        self.assertEqual(ctx.exception.code, "revision_conflict")

        with self.assertRaises(ConfigError) as ctx:
            self.provider.write(
                "worker", {"concurrency": 99}, revision=result.revision
            )
        self.assertEqual(ctx.exception.code, "schema_invalid")
        on_disk = yaml.safe_load(
            (self.root / "modules" / "worker.yaml").read_text(encoding="utf-8")
        )
        self.assertEqual(on_disk["concurrency"], 4)

    def test_deep_merge_and_null_removal(self):
        effective = self.provider.load()
        result = self.provider.write(
            "api",
            {"session": {"ttlSeconds": 120}, "webRoot": None},
            revision=effective.revisions["api"],
        )
        self.assertEqual(result.data["session"]["cookieName"], "moyu_session")
        self.assertEqual(result.data["session"]["ttlSeconds"], 120)
        self.assertNotIn("webRoot", result.data)

        glob = self.provider.write(
            "global",
            {"modules": {"gateway": True}, "timezone": "Asia/Shanghai"},
            revision=effective.revisions["global"],
        )
        self.assertTrue(glob.data["modules"]["gateway"])
        self.assertEqual(glob.data["modules"]["api"], True)

    def test_secrets_are_not_touched(self):
        secrets = self.root / "secrets"
        secrets.mkdir(parents=True)
        token = secrets / "gateway_reload_token"
        token.write_text("secret-value", encoding="utf-8")
        self.provider.load()
        self.assertEqual(token.read_text(encoding="utf-8"), "secret-value")

    def test_defaults_validate(self):
        for name in DEFAULTS:
            self.provider.validate(name, default_for(name))
        with self.assertRaises(ConfigError) as ctx:
            self.provider.validate("worker", {"schemaVersion": 1, "concurrency": 0})
        self.assertEqual(ctx.exception.code, "schema_invalid")

    def test_last_known_good_missing(self):
        with self.assertRaises(ConfigError) as ctx:
            self.provider.last_known_good("api")
        self.assertEqual(ctx.exception.code, "lkg_missing")


if __name__ == "__main__":
    unittest.main()