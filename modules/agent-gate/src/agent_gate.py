#!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml


def git(root, *args):
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def parse_name_status(output):
    files = []
    for line in output.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        files.append((path, status[0]))
    return files


def staged_files(root):
    return parse_name_status(
        git(root, "diff", "--cached", "--name-status", "-M")
    )


def commit_files(root, commit):
    return parse_name_status(
        git(root, "diff-tree", "--root", "--no-commit-id", "--name-status", "-r", "-M", commit)
    )


def is_merge_commit(root, commit):
    parents = git(root, "rev-list", "--parents", "-n1", commit).split()
    return len(parents) > 2


def parse_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    data = yaml.safe_load(text[4:end])
    return (data or {}), text[end + 5 :]


def module_name(path):
    parts = Path(path).parts
    if len(parts) >= 3 and parts[0] == "modules":
        name = parts[1]
        if name == "_template":
            return None
        return name
    return None


def validate_manifests(root):
    errors = []
    warnings = []
    seen = set()
    for manifest in sorted((root / "modules").glob("*/module.yaml")):
        module_dir = manifest.parent.name
        if module_dir == "_template":
            continue
        try:
            data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            errors.append(f"{manifest}: YAML 解析失败: {exc}")
            continue
        required = [
            "name",
            "status",
            "summary",
            "interfaces",
            "dependencies",
            "docs",
            "history",
            "wiki",
        ]
        missing = [key for key in required if key not in data or data[key] in (None, "")]
        if missing:
            errors.append(f"{manifest}: 缺少字段 {', '.join(missing)}")
            continue
        if data["name"] != module_dir:
            errors.append(f"{manifest}: name={data['name']!r} 与目录 {module_dir!r} 不一致")
        if data["name"] in seen:
            errors.append(f"{manifest}: 模块名重复 {data['name']!r}")
        seen.add(data["name"])
        for key in ("docs", "history", "wiki"):
            target = manifest.parent / data[key]
            if not target.exists():
                errors.append(f"{manifest}: {key} 路径不存在: {data[key]}")
        if module_dir == "_template":
            continue
    return errors, warnings


def check_links(root):
    errors = []
    link_re = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for match in link_re.finditer(text):
            target = match.group(1).split("#")[0].strip()
            if not target or target.startswith(("http://", "https://", "mailto:", "/")):
                continue
            if "<" in target or ">" in target:
                continue
            candidate = (path.parent / target).resolve()
            if not candidate.exists():
                errors.append(f"{path.relative_to(root)}: 链接不存在 {match.group(1)}")
    return errors


def docs_history_leak(root):
    errors = []
    patterns = ["变更记录", "本次修改", "以前是"]
    exempt = ("不写", "不要", "禁止", "避免")
    for path in sorted((root / "docs").rglob("*.md")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(word in line for word in exempt):
                continue
            for pattern in patterns:
                if pattern in line:
                    errors.append(
                        f"{path.relative_to(root)}:{number}: docs 中出现 history 语气: {pattern}"
                    )
    return errors


def check_commit(root, label, files, verbose=False):
    errors = []
    warnings = []
    records = [
        path
        for path, status in files
        if path.startswith("history/commits/") and path.endswith(".md") and status in ("A", "M")
    ]
    if not records:
        errors.append(f"{label}: 缺少 history/commits 记录")
        return errors, warnings

    record_data = {}
    for record in records:
        data, _ = parse_frontmatter(root / record)
        if not data:
            errors.append(f"{record}: 缺少 YAML frontmatter")
            continue
        record_data.update(data)
        for key in ("docs_impact", "wiki_impact"):
            if key not in data:
                errors.append(f"{record}: 缺少 {key}")
        if data.get("docs_impact") is False and not data.get("docs_reason"):
            errors.append(f"{record}: docs_impact=false 但缺少 docs_reason")
        if data.get("wiki_impact") is False and not data.get("wiki_reason"):
            errors.append(f"{record}: wiki_impact=false 但缺少 wiki_reason")

    docs_changed = any(
        path.startswith("docs/") or (path.startswith("modules/") and "/docs/" in path)
        for path, _ in files
    )
    wiki_changed = any(
        path.startswith("wiki/") or (path.startswith("modules/") and "/wiki/" in path)
        for path, _ in files
    )
    if record_data.get("docs_impact") is True and not docs_changed:
        errors.append(f"{label}: docs_impact=true 但没有修改 docs")
    if record_data.get("wiki_impact") is True and not wiki_changed:
        errors.append(f"{label}: wiki_impact=true 但没有修改 wiki")

    affected = sorted({m for path, _ in files if (m := module_name(path))})
    declared = set(record_data.get("modules") or [])
    for module in affected:
        module_history = [
            path
            for path, status in files
            if path.startswith(f"modules/{module}/history/")
            and path.endswith(".md")
            and not path.endswith("/index.md")
            and status in ("A", "M")
        ]
        if not module_history:
            errors.append(f"{label}: 模块 {module} 改动但没有模块 history")
        if declared and module not in declared:
            errors.append(f"{label}: 模块 {module} 未在提交记录的 modules 中声明")

    if verbose:
        print(f"{label}: files={len(files)} modules={','.join(affected) or '-'}")
    return errors, warnings


def check(root, base=None, staged=False, all_check=False, verbose=False):
    errors, warnings = validate_manifests(root)
    errors.extend(check_links(root))
    errors.extend(docs_history_leak(root))
    if all_check:
        pass
    elif staged:
        files = staged_files(root)
        if files:
            e, w = check_commit(root, "staged", files, verbose)
            errors.extend(e)
            warnings.extend(w)
    else:
        if not base:
            base = "origin/main"
        try:
            commits = git(root, "rev-list", "--reverse", f"{base}..HEAD").split()
        except RuntimeError as exc:
            errors.append(f"无法读取提交范围: {exc}")
            commits = []
        for commit in commits:
            if is_merge_commit(root, commit):
                if verbose:
                    print(f"{commit[:12]}: merge commit，跳过 history 检查")
                continue
            files = commit_files(root, commit)
            e, w = check_commit(root, commit[:12], files, verbose)
            errors.extend(e)
            warnings.extend(w)
    return errors, warnings


def main():
    parser = argparse.ArgumentParser(prog="agent-gate")
    parser.add_argument("command", choices=["check"], nargs="?", default="check")
    parser.add_argument("--root", default=None)
    parser.add_argument("--base", default=None)
    parser.add_argument("--staged", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).resolve() if args.root else Path.cwd()
    errors, warnings = check(
        root,
        base=args.base,
        staged=args.staged,
        all_check=args.all,
        verbose=args.verbose,
    )
    for warning in warnings:
        print(f"WARN {warning}")
    for error in errors:
        print(f"ERROR {error}", file=sys.stderr)
    if errors:
        print(f"agent-gate: FAIL ({len(errors)} errors)", file=sys.stderr)
        return 1
    print("agent-gate: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())