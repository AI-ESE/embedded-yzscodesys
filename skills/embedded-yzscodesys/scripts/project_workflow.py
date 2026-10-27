#!/usr/bin/env python3
"""Offline project/evidence ledger. Checks records; never builds, flashes or authorizes.

Python 3.10+ standard library only. See references/profile-schema.md for the contract.
"""
from __future__ import annotations

import argparse
import copy
import csv
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import sys
import tempfile


SKILL_ROOT = Path(__file__).resolve().parents[1]
GATES = ("intake", "implement", "compile", "flash", "debug")
GOOD = {"passed", "verified", "confirmed", "已通过", "已确认", "已验证", "已核实"}
SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".s", ".asm", ".inc"}
LINKER_SUFFIXES = {".ld", ".lds", ".icf", ".sct", ".cmd", ".xcl"}
CONFIG_SUFFIXES = {".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg", ".conf", ".cmake",
                   ".mk", ".mak", ".uvproj", ".uvprojx", ".uvoptx", ".ewp", ".eww", ".ioc", ".syscfg",
                   ".def", ".opt", ".bat", ".ps1", ".sh", ".py"}
CONFIG_NAMES = {"CMakeLists.txt", "Makefile", "makefile", "Kconfig", "sdkconfig", ".project", ".cproject"}
IGNORED_DIRS = {".git", ".hg", ".svn", "__pycache__", ".cache", ".pytest_cache", "node_modules",
                ".venv", "venv", "build", "dist", "out", ".pio", "cmake-build-debug", "cmake-build-release"}
ROUND_FIELDS = ("status", "evidence", "evidence_sha256", "input_digest", "notes")
FILE_COLUMNS = ["path", "category", "sha256", "context_digest", "applicable_rules", "not_applicable_reason",
                "source_available", "abi_interfaces", "unresolved"]
LOGIC_COLUMNS = ["kind", "id", "source", "code", "item_digest", "verification_level", "unresolved"]
RULE_COLUMNS = ["id", "document", "description", "mode", "rule_digest", "status", "evidence",
                "evidence_sha256", "input_digest", "notes", "unresolved"]
LIMITATION = ("This validates evidence records, file hashes and input binding only; it does not prove code semantics, "
              "electrical correctness, measured timing or hardware behavior, and it grants no execution authorization.")


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _inside(path, root):
    return path == root or root in path.parents


def _root(profile):
    raw = profile.get("project_root", "")
    if not isinstance(raw, str) or not raw or not Path(raw).is_absolute():
        raise ValueError("project_root must be an absolute existing directory")
    root = Path(raw).resolve()
    if not root.is_dir():
        raise ValueError("project_root is not a directory")
    return root


def _output(profile):
    raw = profile.get("output_dir", "")
    if not isinstance(raw, str) or not raw or not Path(raw).is_absolute():
        raise ValueError("output_dir must be an absolute directory")
    output = Path(raw).resolve()
    if output == _root(profile):
        raise ValueError("output_dir must be a dedicated directory, different from project_root")
    return output


def _path(profile, value, *, output_only=False):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing file path")
    candidate = Path(value)
    if ".." in candidate.parts:
        raise ValueError("path traversal is not allowed: " + value)
    result = (candidate if candidate.is_absolute() else _root(profile) / candidate).resolve()
    allowed = [_output(profile)] if output_only else [_root(profile), _output(profile)]
    if not any(_inside(result, base) for base in allowed):
        raise ValueError("path escapes project/output boundary: " + value)
    return result


def _display(profile, path):
    try:
        return path.relative_to(_root(profile)).as_posix()
    except ValueError:
        return str(path)


def _graph_path(profile, value):
    """Match the renderer: graph references are relative to the real profile/output directory."""
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError("graph file path is required")
    relative = Path(value.replace("\\", "/"))
    if ":" in value or relative.is_absolute() or PureWindowsPath(value).is_absolute() or ".." in relative.parts:
        raise ValueError("graph paths must be relative and stay inside output_dir: " + value)
    output = _output(profile)
    path = (output / relative).resolve()
    if not _inside(path, output):
        raise ValueError("graph file escapes output_dir: " + value)
    if not path.is_file() or not path.stat().st_size:
        raise ValueError("graph file missing or empty: " + value)
    return path


def _graph_reference(profile, item, *, required):
    result = copy.deepcopy(item)
    if required or "path" in item:
        result["actual_sha256"] = _sha(_graph_path(profile, item.get("path")))
    return result


def _load_profile(profile_path):
    path = Path(profile_path).resolve()
    profile = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(profile, dict):
        raise ValueError("profile must be a JSON object")
    if path.parent != _output(profile):
        raise ValueError("profile file directory must match declared output_dir")
    return profile


def _actual_reference(profile, item):
    result = copy.deepcopy(item)
    if item.get("path"):
        path = _path(profile, item["path"])
        result["actual_sha256"] = _sha(path) if path.is_file() else "missing"
    else:
        result["actual_sha256"] = "missing"
    return result


def approval_digest(profile: dict) -> str:
    """Hash the reviewed plan and real document/diagram bytes, excluding implementation source bytes.

    approvals[].input_digest stores this digest. Normal source edits leave it unchanged.
    """
    plan = {key: copy.deepcopy(profile.get(key)) for key in (
        "schema_version", "project_name", "project_root", "revision", "mcu", "toolchain", "work", "architecture")}
    plan["documents"] = [_actual_reference(profile, item) for item in profile.get("documents", [])]
    plan["pins"] = [{key: value for key, value in item.items() if key != "review_status"}
                    for item in profile.get("pins", [])]
    plan["logic"] = profile.get("logic", [])
    plan["diagrams"] = [_graph_reference(profile, item, required=True) for item in profile.get("diagrams", [])]
    plan["waveforms"] = [_graph_reference(profile, item, required=False) for item in profile.get("waveforms", [])]
    return _hash(plan)


def _category(path):
    suffix = path.suffix.lower()
    if suffix in LINKER_SUFFIXES:
        return "linker"
    if suffix in {".s", ".asm"} or path.name.lower().startswith("startup"):
        return "startup"
    if suffix in {".h", ".hh", ".hpp", ".hxx", ".inc"}:
        category = "header"
    elif suffix in SOURCE_SUFFIXES:
        category = "source"
    else:
        category = "configuration"
    if any(part.lower() in {"sdk", "vendor", "third_party", "third-party", "cmsis"} for part in path.parts):
        return "sdk-" + category
    return category


def _scan(profile):
    root, output = _root(profile), _output(profile)
    work = profile.get("work", {})
    roots = work.get("source_roots", ["."])
    excludes = work.get("exclude", [])
    if not isinstance(roots, list) or not roots:
        raise ValueError("work.source_roots must be a nonempty list")
    if not isinstance(excludes, list) or any(not isinstance(item, str) for item in excludes):
        raise ValueError("work.exclude must be a list of patterns")
    found = {}
    for entry in roots:
        start = _path(profile, entry)
        if not _inside(start, root) or not start.is_dir():
            raise ValueError("source root must be an existing directory inside project_root: " + str(entry))
        for directory, dirs, files in os.walk(start, followlinks=False):
            parent = Path(directory)
            dirs[:] = sorted(name for name in dirs if name.lower() not in IGNORED_DIRS
                             and not (parent / name).is_symlink()
                             and not _inside((parent / name).resolve(), output)
                             and not any(fnmatch.fnmatch((parent / name).relative_to(root).as_posix(), pattern)
                                         for pattern in excludes))
            for name in sorted(files):
                path = parent / name
                relative = path.relative_to(root).as_posix()
                if path.is_symlink():
                    raise ValueError("source file symlinks must be materialized before review: " + relative)
                if _inside(path.resolve(), output) or any(fnmatch.fnmatch(relative, pattern) for pattern in excludes):
                    continue
                if path.suffix.lower() in SOURCE_SUFFIXES | LINKER_SUFFIXES | CONFIG_SUFFIXES or name in CONFIG_NAMES:
                    found[relative] = {"path": relative, "category": _category(path.relative_to(root)), "sha256": _sha(path),
                                       "source_available": "yes", "abi_interfaces": ""}
    for item in work.get("precompiled_libraries", []):
        path = _path(profile, item["path"])
        if not path.is_file():
            raise ValueError("precompiled library file missing: " + str(item["path"]))
        relative = _display(profile, path)
        found[relative] = {"path": relative, "category": "precompiled-library", "sha256": _sha(path),
                           "source_available": "no", "abi_interfaces": item.get("abi_interfaces", "")}
    return [found[key] for key in sorted(found)]


def input_digest(profile: dict) -> str:
    """Hash the current reviewed plan plus actual source/config/library manifest.

    No approvals, CSV results, build results, authorization or debug results enter this digest.
    Evidence hashes are validated separately, so their contents cannot silently change.
    """
    return _hash({"approval_digest": approval_digest(profile), "files": _scan(profile)})


def _round_columns(base, rounds):
    return base + [round_id + "_" + field for round_id in rounds for field in ROUND_FIELDS]


def _blank_rounds(row, rounds):
    for round_id in rounds:
        for field in ROUND_FIELDS:
            row[round_id + "_" + field] = "pending" if field == "status" else ""
    return row


def _read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _atomic_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
        temporary.replace(path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _write_json(path, profile):
    _atomic_text(path, json.dumps(profile, ensure_ascii=False, indent=2) + "\n")


def _write_csv(path, columns, rows):
    import io
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    _atomic_text(path, handle.getvalue())


def _catalog():
    path = SKILL_ROOT / "assets" / "rule-catalog.json"
    if not path.is_file():
        return []
    catalog = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(catalog, list):
        raise ValueError("rule catalog must be a list")
    seen = set()
    for item in catalog:
        if not isinstance(item, dict) or any(not item.get(key) for key in ("id", "document", "description", "mode")):
            raise ValueError("rule catalog has incomplete entries")
        if item["id"] in seen:
            raise ValueError("rule catalog has duplicate IDs: " + item["id"])
        seen.add(item["id"])
    return catalog


def _rule_digest(definition):
    """Bind coverage to the actual bundled normative text, independently of plan approval."""
    value = definition["document"]
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError("rule source document path is required: " + str(definition.get("id")))
    relative = Path(value.replace("\\", "/"))
    if ":" in value or relative.is_absolute() or PureWindowsPath(value).is_absolute() or ".." in relative.parts:
        raise ValueError("rule source document path must stay inside the skill: " + value)
    root = SKILL_ROOT.resolve()
    path = (root / relative).resolve()
    if not _inside(path, root) or not path.is_file() or not path.stat().st_size:
        raise ValueError("rule source document missing, empty or outside skill: " + value)
    return _hash({"definition": definition, "document_sha256": _sha(path)})


def _items(profile, current_digest):
    rows = []
    for kind, key in (("logic", "logic"), ("pin", "pins")):
        seen = set()
        for item in profile.get(key, []):
            identity = item.get("id", "")
            if not identity or identity in seen:
                raise ValueError("missing or duplicate " + kind + " id")
            seen.add(identity)
            item_data = {k: v for k, v in item.items() if k != "review_status"}
            row = {"kind": kind, "id": identity, "source": str(item.get("source", "")), "code": str(item.get("code", "")),
                   "item_digest": _hash({"item": item_data, "inputs": current_digest}),
                   "verification_level": "software-analysis", "unresolved": ""}
            rows.append(_blank_rounds(row, ("L1", "L2", "L3")))
    return rows


def _evidence_ok(profile, path_value, recorded_hash):
    try:
        path = _path(profile, path_value)
        return path.is_file() and path.stat().st_size > 0 and bool(recorded_hash) and _sha(path) == recorded_hash
    except (OSError, ValueError, TypeError):
        return False


def _preserve_rounds(profile, row, old, rounds, marker):
    if not old or old.get(marker) != row.get(marker):
        return row
    if row.get("context_digest") != old.get("context_digest"):
        return row
    for round_id in rounds:
        if old.get(round_id + "_input_digest") == row[marker] and _evidence_ok(
                profile, old.get(round_id + "_evidence"), old.get(round_id + "_evidence_sha256")):
            for field in ROUND_FIELDS:
                row[round_id + "_" + field] = old.get(round_id + "_" + field, "")
    for key in ("applicable_rules", "not_applicable_reason", "unresolved", "verification_level", "abi_interfaces"):
        if key in old and key in row:
            row[key] = old[key]
    return row


def _index(rows, keys):
    indexed = {}
    for row in rows:
        identity = tuple(row.get(key, "") for key in keys)
        if any(not value for value in identity) or identity in indexed:
            raise ValueError("missing or duplicate CSV identity: " + repr(identity))
        indexed[identity] = row
    return indexed


def snapshot(profile_path):
    profile_path = Path(profile_path).resolve()
    profile = _load_profile(profile_path)
    current, context = input_digest(profile), approval_digest(profile)
    review = profile["review"]
    paths = {key: _path(profile, review[key], output_only=True)
             for key in ("inventory_path", "logic_pins_path", "rule_coverage_path")}
    old_files = _index(_read_csv(paths["inventory_path"]), ["path"]) if paths["inventory_path"].exists() else {}
    files = []
    for entry in _scan(profile):
        row = {**entry, "context_digest": context, "applicable_rules": "", "not_applicable_reason": "", "unresolved": ""}
        _blank_rounds(row, ("C1", "C2", "C3"))
        if entry["category"] == "precompiled-library":
            row["not_applicable_reason"] = "Internal source unavailable; only ABI, public interfaces and integration are reviewed."
        files.append(_preserve_rounds(profile, row, old_files.get((entry["path"],)), ("C1", "C2", "C3"), "sha256"))
    old_items = _index(_read_csv(paths["logic_pins_path"]), ["kind", "id"]) if paths["logic_pins_path"].exists() else {}
    items = [_preserve_rounds(profile, row, old_items.get((row["kind"], row["id"])), ("L1", "L2", "L3"), "item_digest")
             for row in _items(profile, current)]
    old_rules = _index(_read_csv(paths["rule_coverage_path"]), ["id"]) if paths["rule_coverage_path"].exists() else {}
    rules = []
    for definition in _catalog():
        row = {key: str(definition[key]) for key in ("id", "document", "description", "mode")}
        row.update(rule_digest=_rule_digest(definition), status="pending", evidence="", evidence_sha256="", input_digest="", notes="", unresolved="")
        old = old_rules.get((row["id"],))
        if old and old.get("rule_digest") == row["rule_digest"] and old.get("input_digest") == current and _evidence_ok(
                profile, old.get("evidence"), old.get("evidence_sha256")):
            for key in ("status", "evidence", "evidence_sha256", "input_digest", "notes", "unresolved"):
                row[key] = old.get(key, "")
        rules.append(row)
    _write_csv(paths["inventory_path"], _round_columns(FILE_COLUMNS, ("C1", "C2", "C3")), files)
    _write_csv(paths["logic_pins_path"], _round_columns(LOGIC_COLUMNS, ("L1", "L2", "L3")), items)
    _write_csv(paths["rule_coverage_path"], RULE_COLUMNS, rules)
    return {"ok": True, "profile": str(profile_path), "files": len(files), "logic_pins": len(items), "rules": len(rules),
            "input_digest": current, "approval_digest": context,
            "warnings": [] if rules else ["Rule catalog missing or empty; compile and later gates will fail."]}


def initialize(project_root, output, name):
    root, output = Path(project_root).resolve(), Path(output).resolve()
    if not root.is_dir():
        raise ValueError("project root must already exist")
    if root == output:
        raise ValueError("output must be a dedicated directory")
    if output.exists() and any(output.iterdir()):
        raise ValueError("refusing to overwrite nonempty output directory")
    profile = json.loads((SKILL_ROOT / "assets" / "project-profile.json").read_text(encoding="utf-8-sig"))
    profile.update(project_name=name, project_root=str(root), output_dir=str(output))
    for key, filename in (("inventory_path", "review-files.csv"), ("logic_pins_path", "review-logic-pins.csv"),
                          ("rule_coverage_path", "rule-coverage.csv")):
        profile["review"][key] = _display(profile, output / filename)
    profile_path = output / "project-profile.json"
    _write_json(profile_path, profile)
    return snapshot(profile_path)


def _require(errors, condition, message):
    if not condition:
        errors.append(message)


def _has(value):
    return isinstance(value, str) and bool(value.strip())


def _proof(profile, errors, label, value, digest):
    _require(errors, _evidence_ok(profile, value, digest), label + ": missing, empty, out-of-scope or SHA-256-mismatched evidence")


def _check_intake(profile, errors):
    for key in ("schema_version", "project_name", "revision"):
        _require(errors, _has(profile.get(key)), "missing " + key)
    _require(errors, profile.get("schema_version") == "1.0", "unsupported schema_version")
    mcu, toolchain, work = profile.get("mcu", {}), profile.get("toolchain", {}), profile.get("work", {})
    for key in ("manufacturer", "part_number", "package", "family", "vendor_region", "sdk_ecosystem"):
        _require(errors, _has(mcu.get(key)), "mcu." + key + " is required")
    _require(errors, mcu.get("verified") is True, "MCU identity/package must be verified from actual materials")
    documents = _index(profile.get("documents", []), ["id"])
    for identity in ("datasheet", "schematic"):
        _require(errors, (identity,) in documents, "required document missing: " + identity)
    for item in documents.values():
        label = "document " + item["id"]
        _require(errors, _has(item.get("version")) and item.get("status") in GOOD, label + " version and verified status required")
        _proof(profile, errors, label, item.get("path"), item.get("sha256"))
    for key in ("ide", "version", "compiler", "compiler_version", "sdk", "sdk_version", "optimization", "build_configuration"):
        _require(errors, _has(toolchain.get(key)), "toolchain." + key + " is required (explicit 'none' if justified)")
    _require(errors, toolchain.get("compatible") is True and _has(toolchain.get("compatibility_evidence")),
             "IDE/compiler/SDK compatibility with the exact MCU requires an analysis record")
    _require(errors, work.get("kind") in {"new", "refactor", "port"}, "work.kind must be new/refactor/port")
    _require(errors, work.get("system") in {"bare-metal", "freertos"}, "work.system must be bare-metal/freertos")
    if work.get("kind") in {"refactor", "port"}:
        for key in ("original_source_path", "original_system", "original_analysis"):
            _require(errors, _has(work.get(key)), "work." + key + " is required for original-project analysis")
        if work.get("original_source_path"):
            _require(errors, Path(work["original_source_path"]).is_dir(), "original_source_path directory missing")
        _proof(profile, errors, "original-project read analysis", work.get("original_analysis"), work.get("original_analysis_sha256"))


def _check_implementation(profile, errors, plan_digest):
    architecture = profile.get("architecture", {})
    for key in ("summary", "modules", "tasks", "data_flows"):
        _require(errors, bool(architecture.get(key)), "architecture." + key + " is required")
    _require(errors, isinstance(architecture.get("interrupts"), list), "architecture.interrupts must explicitly list interrupts (or [])")
    _require(errors, bool(profile.get("pins")), "complete physical pin inventory is required")
    _require(errors, bool(profile.get("logic")), "business logic inventory is required")
    for pin in profile.get("pins", []):
        for key in ("id", "physical_pin", "gpio", "function", "net", "direction", "active_level", "inversion", "pull",
                    "reset_state", "run_state", "fault_state", "source", "code"):
            _require(errors, _has(pin.get(key)), "pin " + str(pin.get("id")) + " missing " + key + " (state explicit N/A with reason where justified)")
        _require(errors, pin.get("review_status") in GOOD, "pin " + str(pin.get("id")) + " is not confirmed")
    pin_ids = {pin.get("id") for pin in profile.get("pins", [])}
    for logic in profile.get("logic", []):
        for key in ("id", "description", "requirements", "source", "code"):
            _require(errors, bool(logic.get(key)), "logic " + str(logic.get("id")) + " missing " + key)
        _require(errors, isinstance(logic.get("pin_ids"), list) and set(logic.get("pin_ids", [])).issubset(pin_ids),
                 "logic pin_ids must reference defined pins")
    approvals = _index(profile.get("approvals", []), ["stage"])
    for stage in ("A1", "A2", "A3", "A4", "A5"):
        row = approvals.get((stage,), {})
        _require(errors, row.get("status") in GOOD and row.get("revision") == profile.get("revision")
                 and row.get("input_digest") == plan_digest, stage + ": current reviewed plan/revision confirmation required")
        _proof(profile, errors, stage + " actual user confirmation", row.get("user_evidence"), row.get("user_evidence_sha256"))


def _rounds(profile, errors, row, label, rounds, marker):
    hashes = []
    _require(errors, not row.get("unresolved", "").strip(), label + ": unresolved items remain")
    for round_id in rounds:
        prefix = round_id + "_"
        _require(errors, row.get(prefix + "status") in GOOD, label + ": " + round_id + " not passed")
        _require(errors, row.get(prefix + "input_digest") == marker, label + ": " + round_id + " stale input digest")
        _proof(profile, errors, label + " " + round_id, row.get(prefix + "evidence"), row.get(prefix + "evidence_sha256"))
        hashes.append(row.get(prefix + "evidence_sha256", ""))
    _require(errors, len(set(hashes)) == len(rounds), label + ": rounds require distinct evidence contents, not copies of one log")


def _check_project_logs(profile, errors):
    """Check basic record labels/values only; do not claim complete or append-only history."""
    folder = _root(profile) / "Log"
    specifications = (
        ("版本记录.md", ("版本号", "修改日期", "修改涉及文件", "修改内容或者功能")),
        ("提示词记录.md", ("提示词时间", "精简提示词内容", "最终改善输出")),
    )
    ordinary_folder = folder.is_dir() and not folder.is_symlink() and folder.resolve() == folder
    for filename, labels in specifications:
        path = folder / filename
        label = "Log/" + filename
        ordinary_file = ordinary_folder and path.is_file() and not path.is_symlink() and path.resolve() == path
        _require(errors, ordinary_file, label + ": required ordinary project Log file missing or unsafe")
        if not ordinary_file:
            continue
        content = path.read_text(encoding="utf-8-sig")
        _require(errors, bool(content.strip()), label + ": project Log record is empty")
        pattern = re.compile(r"(?m)^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?(" +
                             "|".join(re.escape(value) for value in labels) +
                             r")(?:\*\*)?[ \t]*[：:][ \t]*")
        matches = list(pattern.finditer(content))
        populated = set()
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            if content[match.end():end].strip():
                populated.add(match.group(1))
        for field in labels:
            _require(errors, field in populated, label + ": required nonempty field record missing: " + field)


def _check_reviews(profile, errors, current, plan_digest):
    review = profile.get("review", {})
    files = _scan(profile)
    file_rows = _index(_read_csv(_path(profile, review.get("inventory_path"), output_only=True)), ["path"])
    _require(errors, any(item["category"] != "precompiled-library" for item in files),
             "current source/header/startup/linker/config inventory is empty (binary libraries alone are insufficient)")
    _require(errors, set(file_rows) == {(row["path"],) for row in files}, "file inventory differs from current scan; run snapshot and review new/changed files")
    for item in files:
        row = file_rows.get((item["path"],), {})
        _require(errors, row.get("sha256") == item["sha256"] and row.get("context_digest") == plan_digest,
                 item["path"] + ": stale file or plan digest")
        _require(errors, _has(row.get("applicable_rules")), item["path"] + ": file-specific rule applicability analysis required")
        _rounds(profile, errors, row, item["path"], ("C1", "C2", "C3"), item["sha256"])
        if item["category"] == "precompiled-library":
            _require(errors, row.get("source_available") == "no" and _has(row.get("abi_interfaces"))
                     and _has(row.get("not_applicable_reason")), item["path"] + ": binary ABI/interfaces and unavailable internal source must be recorded")
    expected = _items(profile, current)
    logic_rows = _index(_read_csv(_path(profile, review.get("logic_pins_path"), output_only=True)), ["kind", "id"])
    _require(errors, bool(expected) and set(logic_rows) == {(row["kind"], row["id"]) for row in expected},
             "logic/pin inventory must exactly cover every current logic and pin")
    for item in expected:
        row = logic_rows.get((item["kind"], item["id"]), {})
        label = item["kind"] + " " + item["id"]
        _require(errors, row.get("item_digest") == item["item_digest"], label + ": stale logic/pin inputs")
        _rounds(profile, errors, row, label, ("L1", "L2", "L3"), item["item_digest"])
    catalog = _catalog()
    _require(errors, bool(catalog), "rule catalog missing or empty; rule coverage cannot be established")
    coverage = _index(_read_csv(_path(profile, review.get("rule_coverage_path"), output_only=True)), ["id"])
    _require(errors, set(coverage) == {(rule["id"],) for rule in catalog}, "rule coverage missing, extra or obsolete catalog entries")
    for rule in catalog:
        row = coverage.get((rule["id"],), {})
        label = "rule " + rule["id"]
        _require(errors, row.get("rule_digest") == _rule_digest(rule) and row.get("input_digest") == current,
                 label + ": stale definition or input digest")
        status = row.get("status")
        _require(errors, status in GOOD or (status == "not_applicable" and _has(row.get("notes"))),
                 label + ": coverage outcome or specific N/A reason required")
        _require(errors, not row.get("unresolved", "").strip(), label + ": unresolved items remain")
        _proof(profile, errors, label, row.get("evidence"), row.get("evidence_sha256"))


def _check_build_and_flash(profile, errors, current):
    build, hardware, toolchain = profile.get("build", {}), profile.get("hardware", {}), profile.get("toolchain", {})
    _require(errors, build.get("status") in GOOD and type(build.get("exit_code")) is int and build["exit_code"] == 0
             and type(build.get("error_count")) is int and build["error_count"] == 0 and build.get("production") is True,
             "current production build requires successful status, exit_code=0, error_count=0 and production=true")
    _require(errors, build.get("configuration") == toolchain.get("build_configuration")
             and build.get("optimization") == toolchain.get("optimization") and build.get("input_digest") == current,
             "build configuration/optimization/current inputs do not match")
    _require(errors, build.get("warnings_reviewed") is True and build.get("optimizer_reviewed") is True,
             "warning and optimizer analysis must be recorded")
    _proof(profile, errors, "build log", build.get("log"), build.get("log_sha256"))
    _proof(profile, errors, "firmware artifact", build.get("artifact"), build.get("artifact_sha256"))
    _require(errors, hardware.get("target_identified") is True and hardware.get("connection_confirmed_by_user") is True,
             "actual current target and user-confirmed wiring required")
    for key in ("target_part", "target_board", "probe"):
        _require(errors, _has(hardware.get(key)), "hardware." + key + " is required")
    _require(errors, hardware.get("target_part") == profile.get("mcu", {}).get("part_number"), "hardware target part differs from reviewed MCU")
    regions = hardware.get("flash_regions")
    regions_valid = isinstance(regions, list) and bool(regions)
    if regions_valid:
        for region in regions:
            try:
                start = int(str(region["start"]), 0)
                length = int(str(region["length"]), 0)
                regions_valid = regions_valid and start >= 0 and length > 0
            except (KeyError, ValueError, TypeError):
                regions_valid = False
    _require(errors, regions_valid, "explicit flash regions require nonnegative start and positive length; no implicit mass erase")
    auth = hardware.get("flash_authorization")
    if not isinstance(auth, dict):
        errors.append("flash authorization must be an explicit target/artifact/region-bound evidence record")
        return
    _require(errors, auth.get("status") in GOOD and auth.get("input_digest") == current
             and auth.get("artifact_sha256") == build.get("artifact_sha256") and auth.get("flash_regions") == regions
             and all(auth.get(key) == hardware.get(key) for key in ("target_part", "target_board", "probe")),
             "flash authorization is absent or stale for current inputs/artifact/target/probe/regions")
    _proof(profile, errors, "flash user authorization", auth.get("user_evidence"), auth.get("user_evidence_sha256"))


def check_profile(profile_path, gate) -> dict:
    """Return JSON-serializable readiness of records only. No external command or mutation occurs."""
    errors = []
    result = {"ok": False, "gate": gate, "errors": errors, "limitations": [LIMITATION]}
    try:
        if gate not in GATES:
            raise ValueError("unknown gate: " + str(gate))
        profile = _load_profile(profile_path)
        _root(profile)
        _output(profile)
        current, plan_digest = input_digest(profile), approval_digest(profile)
        result.update(input_digest=current, approval_digest=plan_digest)
        _check_intake(profile, errors)
        if GATES.index(gate) >= 1:
            _check_implementation(profile, errors, plan_digest)
        if GATES.index(gate) >= 2:
            _check_project_logs(profile, errors)
            _check_reviews(profile, errors, current, plan_digest)
        if GATES.index(gate) >= 3:
            _check_build_and_flash(profile, errors, current)
        if gate == "debug":
            hardware = profile.get("hardware", {})
            channel = hardware.get("debug_connection")
            _require(errors, isinstance(channel, dict) and _has(channel.get("channel")) and _has(channel.get("port"))
                     and all(channel.get(key) == hardware.get(key) for key in ("target_part", "target_board")),
                     "debug requires a concrete supported channel, port/configuration and matching current target")
            if hardware.get("debug_log") or hardware.get("debug_log_sha256"):
                _proof(profile, errors, "debug observation log", hardware.get("debug_log"), hardware.get("debug_log_sha256"))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors.append(str(exc))
    result["ok"] = not errors
    if result["ok"]:
        result["ready_for"] = gate
    return result


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"ok": False, "errors": [message]}, ensure_ascii=False))
        raise SystemExit(2)


def main(argv=None):
    parser = _Parser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init_parser = commands.add_parser("init")
    init_parser.add_argument("--project-root", required=True)
    init_parser.add_argument("--output", required=True)
    init_parser.add_argument("--name", required=True)
    snapshot_parser = commands.add_parser("snapshot")
    snapshot_parser.add_argument("--profile", required=True)
    check_parser = commands.add_parser("check")
    check_parser.add_argument("--profile", required=True)
    check_parser.add_argument("--gate", choices=GATES, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            result = initialize(args.project_root, args.output, args.name)
        elif args.command == "snapshot":
            result = snapshot(args.profile)
        else:
            result = check_profile(args.profile, args.gate)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = {"ok": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
