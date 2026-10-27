"""Behavior tests for the offline evidence ledger; no hardware or IDE is used."""
import csv
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "project_workflow.py"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII=")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class ProjectWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="workflow-test-", dir=SKILL / "tests")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "firmware"
        self.root.mkdir()
        self.output = self.root / "review"
        self.profile_path = self.output / "project-profile.json"

    def cli(self, *args):
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), *map(str, args)],
                                capture_output=True, text=True, encoding="utf-8")
        return result

    def init(self):
        result = self.cli("init", "--project-root", self.root, "--output", self.output,
                          "--name", "bench")
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(self.profile_path.read_text(encoding="utf-8"))

    def save(self, profile):
        self.profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    def api(self):
        spec = importlib.util.spec_from_file_location("tested_project_workflow", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def snapshot(self):
        result = self.cli("snapshot", "--profile", self.profile_path)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(self.profile_path.read_text(encoding="utf-8"))

    def evidence(self, name, text):
        path = self.output / "evidence" / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return str(path.relative_to(self.root)).replace("\\", "/"), sha(path)

    def ready(self):
        """A real but tiny evidence fixture, deliberately not a simulated MCU result."""
        (self.root / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
        (self.root / "sdk").mkdir()
        (self.root / "sdk" / "device.h").write_text("#define DEVICE_TEST 1\n", encoding="utf-8")
        log_dir = self.root / "Log"
        log_dir.mkdir()
        (log_dir / "版本记录.md").write_text(
            "# 版本记录\n\n版本号：v1\n修改日期：2026-10-27\n修改涉及文件：\n- main.c\n修改内容或者功能：\nFixture implementation\n",
            encoding="utf-8")
        (log_dir / "提示词记录.md").write_text(
            "# 提示词记录\n\n提示词时间：2026-10-27T10:00:00+08:00\n精简提示词内容：\nFixture request\n最终改善输出：\nFixture output\n",
            encoding="utf-8")
        profile = self.init()
        profile["revision"] = "v1"
        profile["mcu"].update(manufacturer="Fixture vendor", part_number="PART-TEST", package="QFN-1",
                              family="fixture", vendor_region="other", sdk_ecosystem="fixture",
                              verified=True)
        for doc in profile["documents"]:
            path = self.root / (doc["id"] + ".txt")
            path.write_text("Fixture " + doc["id"] + " version 1", encoding="utf-8")
            doc.update(path=path.name, version="1", sha256=sha(path), status="verified")
        profile["toolchain"].update(ide="VS Code", version="fixture", compiler="fixture cc",
                                     compiler_version="1", sdk="fixture sdk", sdk_version="1",
                                     optimization="-O2", build_configuration="Release",
                                     compatible=True, compatibility_evidence="fixture part supported")
        profile["work"].update(kind="new", system="bare-metal")
        profile["architecture"].update(summary="fixture scheduling", modules=[{"id": "APP", "layer": "APP"}],
                                        tasks=[{"id": "main", "trigger": "loop"}],
                                        interrupts=[], data_flows=["main -> APP"])
        profile["pins"] = [{"id": "P1", "physical_pin": "1", "gpio": "PA0", "function": "test",
                            "net": "TEST", "direction": "output", "active_level": "high", "inversion": "none",
                            "pull": "none", "reset_state": "low", "run_state": "high", "fault_state": "low",
                            "source": "schematic.txt page 1", "code": "main.c:1", "review_status": "confirmed"}]
        profile["logic"] = [{"id": "LOG1", "description": "fixture output", "requirements": "fixture requirement",
                             "source": "datasheet.txt", "code": "main.c:1", "pin_ids": ["P1"]}]
        self.save(profile)
        profile = self.snapshot()
        api = self.api()
        digest = api.input_digest(profile)
        for stage in profile["approvals"]:
            path, digest_evidence = self.evidence(stage["stage"] + ".txt", "Fixture human confirmation " + stage["stage"])
            stage.update(status="confirmed", revision="v1", input_digest=api.approval_digest(profile),
                         user_evidence=path, user_evidence_sha256=digest_evidence)
        self.save(profile)
        for key, rounds in [("inventory_path", ("C1", "C2", "C3")),
                            ("logic_pins_path", ("L1", "L2", "L3"))]:
            target = self.root / profile["review"][key]
            rows = read_csv(target)
            for index, row in enumerate(rows):
                if key == "inventory_path":
                    row["applicable_rules"] = "See current rule coverage; applicable code and integration rules"
                for round_id in rounds:
                    path, evidence_hash = self.evidence(f"{key}-{index}-{round_id}.txt",
                                                        f"Fixture analysis {key} {index} {round_id}")
                    row[round_id + "_status"] = "passed"
                    row[round_id + "_evidence"] = path
                    row[round_id + "_evidence_sha256"] = evidence_hash
                    row[round_id + "_input_digest"] = row["sha256"] if key == "inventory_path" else row["item_digest"]
            write_csv(target, rows)
        target = self.root / profile["review"]["rule_coverage_path"]
        rows = read_csv(target)
        self.assertTrue(rows, "The installed rule catalog must not be empty")
        path, evidence_hash = self.evidence("rule-coverage.txt", "Fixture analysis per rule:\n" +
                                            "\n".join(row["id"] + ": fixture applicability analysis" for row in rows))
        for row in rows:
            row.update(status="passed", evidence=path, evidence_sha256=evidence_hash, input_digest=digest)
        write_csv(target, rows)
        log, log_hash = self.evidence("build.txt", "Fixture compiler log: 0 errors")
        artifact, artifact_hash = self.evidence("firmware.bin", "Fixture bytes, not executable firmware")
        profile["build"].update(status="passed", exit_code=0, configuration="Release", optimization="-O2",
                                input_digest=digest, log=log, log_sha256=log_hash,
                                artifact=artifact, artifact_sha256=artifact_hash,
                                warnings_reviewed=True, optimizer_reviewed=True,
                                production=True, error_count=0)
        profile["hardware"].update(target_identified=True, target_part="PART-TEST", target_board="Fixture board",
                                   probe="Fixture probe", connection_confirmed_by_user=True,
                                   flash_authorization={"status": "confirmed", "input_digest": digest,
                                                        "artifact_sha256": artifact_hash, "target_part": "PART-TEST",
                                                        "target_board": "Fixture board", "probe": "Fixture probe",
                                                        "flash_regions": [{"start": "0x0", "length": "0x100"}],
                                                        "user_evidence": profile["approvals"][4]["user_evidence"],
                                                        "user_evidence_sha256": profile["approvals"][4]["user_evidence_sha256"]},
                                   flash_regions=[{"start": "0x0", "length": "0x100"}],
                                   debug_connection={"channel": "UART", "port": "fixture", "baud": 115200,
                                                     "target_part": "PART-TEST", "target_board": "Fixture board"})
        self.save(profile)
        return profile

    def check(self, gate):
        return self.api().check_profile(self.profile_path, gate)

    def assert_rejected(self, gate):
        result = self.check(gate)
        self.assertFalse(result["ok"], result)
        self.assertTrue(result["errors"])

    def test_init_is_only_an_unapproved_document_bundle(self):
        profile = self.init()
        self.assertEqual(profile["project_name"], "bench")
        self.assertEqual(list(self.root.glob("*.c")), [])
        result = self.cli("check", "--profile", self.profile_path, "--gate", "implement")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertFalse(json.loads(result.stdout)["ok"])

    def test_complete_real_evidence_fixture_passes_all_record_gates(self):
        self.ready()
        for gate in ["intake", "implement", "compile", "flash", "debug"]:
            with self.subTest(gate=gate):
                result = self.check(gate)
                self.assertTrue(result["ok"], result)
                self.assertEqual(result.get("ready_for"), gate)

    def test_snapshot_includes_sdk_startup_linker_and_config_but_excludes_own_output(self):
        self.init()
        for path in ["src/main.c", "sdk/device.h", "startup/startup.S", "linker/device.ld", "CMakeLists.txt",
                     "build/cache.c", ".git/untracked.c", "review/internal.c", "blob.bin"]:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(path, encoding="utf-8")
        profile = self.snapshot()
        rows = read_csv(self.root / profile["review"]["inventory_path"])
        self.assertEqual({r["path"] for r in rows}, {"src/main.c", "sdk/device.h", "startup/startup.S",
                                                     "linker/device.ld", "CMakeLists.txt"})

    def test_empty_source_inventory_cannot_pass_compile(self):
        profile = self.ready()
        (self.root / "main.c").unlink()
        (self.root / "sdk" / "device.h").unlink()
        self.snapshot()
        self.assert_rejected("compile")

    def test_precompiled_binary_alone_is_not_a_source_review_scope(self):
        profile = self.ready()
        (self.root / "main.c").unlink()
        (self.root / "sdk" / "device.h").unlink()
        (self.root / "vendor.lib").write_bytes(b"fixture library")
        profile["work"]["precompiled_libraries"] = [{"path": "vendor.lib", "abi_interfaces": "fixture ABI"}]
        self.save(profile)
        self.snapshot()
        result = self.check("compile")
        self.assertFalse(result["ok"])
        self.assertTrue(any("source/header/startup/linker/config inventory is empty" in error for error in result["errors"]), result)

    def test_reused_round_report_is_rejected_even_with_matching_hashes(self):
        profile = self.ready()
        path = self.root / profile["review"]["inventory_path"]
        rows = read_csv(path)
        rows[0]["C2_evidence"] = rows[0]["C1_evidence"]
        rows[0]["C2_evidence_sha256"] = rows[0]["C1_evidence_sha256"]
        write_csv(path, rows)
        self.assert_rejected("compile")

    def test_each_file_requires_recorded_rule_applicability(self):
        profile = self.ready()
        path = self.root / profile["review"]["inventory_path"]
        rows = read_csv(path)
        rows[0]["applicable_rules"] = ""
        write_csv(path, rows)
        self.assert_rejected("compile")

    def test_distinct_paths_with_duplicate_round_content_are_rejected(self):
        profile = self.ready()
        path = self.root / profile["review"]["logic_pins_path"]
        rows = read_csv(path)
        original = self.root / rows[0]["L1_evidence"]
        duplicate = self.root / rows[0]["L2_evidence"]
        duplicate.write_bytes(original.read_bytes())
        rows[0]["L2_evidence_sha256"] = sha(duplicate)
        write_csv(path, rows)
        self.assert_rejected("compile")

    def test_missing_logic_or_pin_round_is_rejected(self):
        profile = self.ready()
        path = self.root / profile["review"]["logic_pins_path"]
        rows = read_csv(path)
        rows[-1]["L3_status"] = "pending"
        write_csv(path, rows)
        self.assert_rejected("compile")

    def test_changed_source_invalidates_gates_and_its_snapshot_rounds(self):
        profile = self.ready()
        (self.root / "main.c").write_text("int main(void) { return 1; }\n", encoding="utf-8")
        self.assertTrue(self.check("implement")["ok"])
        self.assert_rejected("compile")
        profile = self.snapshot()
        rows = read_csv(self.root / profile["review"]["inventory_path"])
        by_path = {row["path"]: row for row in rows}
        self.assertEqual(by_path["main.c"]["C1_status"], "pending")
        self.assertEqual(by_path["sdk/device.h"]["C1_status"], "passed")

    def test_new_source_file_preserves_plan_approval_but_invalidates_inventory(self):
        self.ready()
        (self.root / "added.c").write_text("int added;\n", encoding="utf-8")
        self.assertTrue(self.check("implement")["ok"])
        self.assert_rejected("compile")

    def test_changed_evidence_content_rejects_stored_round_hash(self):
        profile = self.ready()
        rows = read_csv(self.root / profile["review"]["inventory_path"])
        (self.root / rows[0]["C1_evidence"]).write_text("changed report", encoding="utf-8")
        self.assert_rejected("compile")

    def test_changed_document_rejects_approval_even_after_recorded_hash_updated(self):
        profile = self.ready()
        doc = profile["documents"][0]
        (self.root / doc["path"]).write_text("new datasheet content", encoding="utf-8")
        doc["sha256"] = sha(self.root / doc["path"])
        self.save(profile)
        self.assert_rejected("implement")

    def test_changed_pin_invalidates_rounds(self):
        profile = self.ready()
        profile["pins"][0]["active_level"] = "low"
        self.save(profile)
        self.assert_rejected("implement")
        self.assert_rejected("compile")
        self.snapshot()
        rows = read_csv(self.root / profile["review"]["logic_pins_path"])
        self.assertEqual(next(r for r in rows if r["kind"] == "pin")["L1_status"], "pending")

    def test_revision_two_cannot_reuse_revision_one_approvals(self):
        profile = self.ready()
        profile["revision"] = "v2"
        self.save(profile)
        self.assert_rejected("implement")

    def test_debug_build_cannot_authorize_release_flash(self):
        profile = self.ready()
        profile["build"]["configuration"] = "Debug"
        self.save(profile)
        self.assert_rejected("flash")

    def test_changed_build_log_or_artifact_is_rejected(self):
        profile = self.ready()
        (self.root / profile["build"]["log"]).write_text("other build", encoding="utf-8")
        self.assert_rejected("flash")

    def test_flash_requires_target_bound_user_evidence_and_regions(self):
        profile = self.ready()
        profile["hardware"]["flash_authorization"] = True
        self.save(profile)
        self.assert_rejected("flash")

    def test_debug_requires_actual_configured_channel(self):
        profile = self.ready()
        profile["hardware"]["debug_connection"] = "connected"
        self.save(profile)
        self.assert_rejected("debug")

    def test_path_traversal_in_evidence_or_source_roots_is_rejected(self):
        profile = self.ready()
        profile["approvals"][0]["user_evidence"] = "../outside.txt"
        self.save(profile)
        self.assert_rejected("implement")
        profile["work"]["source_roots"] = ["../"]
        self.save(profile)
        result = self.cli("snapshot", "--profile", self.profile_path)
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_no_rule_row_may_be_omitted(self):
        profile = self.ready()
        path = self.root / profile["review"]["rule_coverage_path"]
        rows = read_csv(path)
        write_csv(path, rows[:-1] or [{**rows[0], "id": "invented-rule"}])
        self.assert_rejected("compile")

    def test_refactor_requires_read_analysis_of_original_project(self):
        profile = self.ready()
        profile["work"].update(kind="refactor", original_source_path="", original_system="")
        self.save(profile)
        self.assert_rejected("implement")

    def test_refactor_analysis_requires_a_real_hashed_artifact(self):
        profile = self.ready()
        profile["work"].update(kind="refactor", original_source_path=str(self.root),
                               original_system="bare-metal", original_analysis="done")
        for row in profile["approvals"]:
            row["input_digest"] = self.api().approval_digest(profile)
        self.save(profile)
        self.assert_rejected("implement")

    def test_refactor_with_recorded_original_analysis_is_ready_for_implementation(self):
        profile = self.ready()
        analysis, digest = self.evidence("original-analysis.txt", "Fixture baseline, actual entry points, scheduling and boundaries")
        profile["work"].update(kind="refactor", original_source_path=str(self.root), original_system="bare-metal",
                               original_analysis=analysis, original_analysis_sha256=digest)
        plan = self.api().approval_digest(profile)
        for row in profile["approvals"]:
            row["input_digest"] = plan
        self.save(profile)
        self.assertTrue(self.check("implement")["ok"], self.check("implement"))

    def test_input_digest_does_not_depend_on_approval_or_build_results(self):
        profile = self.ready()
        api = self.api()
        first = api.input_digest(profile)
        profile["approvals"][0]["status"] = "pending"
        profile["build"]["status"] = "failed"
        profile["hardware"]["verify_result"] = "not run"
        self.assertEqual(api.input_digest(profile), first)

    def test_optimization_change_invalidates_plan_confirmation(self):
        profile = self.ready()
        profile["toolchain"]["optimization"] = "-O3"
        self.save(profile)
        self.assert_rejected("implement")

    def test_ui_round_results_do_not_change_plan_but_selected_style_does(self):
        profile = self.ready()
        profile['architecture']['ui'] = {'enabled': True, 'selected_style': 'S1', 'pages': [{'id': 'P1'}]}
        api = self.api()
        approved = api.approval_digest(profile)
        profile['review']['ui_pages'] = [{'id': 'P1', 'rounds': [{'round': 'U1', 'status': 'pending'}]}]
        self.assertEqual(api.approval_digest(profile), approved)
        profile['architecture']['ui']['selected_style'] = 'S2'
        self.assertNotEqual(api.approval_digest(profile), approved)

    def test_snapshot_preserves_all_unchanged_reviews(self):
        profile = self.ready()
        self.snapshot()
        self.assertTrue(self.check("compile")["ok"], self.check("compile"))
        rows = read_csv(self.root / profile["review"]["logic_pins_path"])
        self.assertEqual({row["L3_status"] for row in rows}, {"passed"})

    def test_snapshot_invalidates_modified_report(self):
        profile = self.ready()
        rows = read_csv(self.root / profile["review"]["inventory_path"])
        (self.root / rows[0]["C1_evidence"]).write_text("edited evidence", encoding="utf-8")
        self.snapshot()
        rows = read_csv(self.root / profile["review"]["inventory_path"])
        self.assertEqual(rows[0]["C1_status"], "pending")
        self.assert_rejected("compile")

    def test_missing_catalog_cannot_pass_compile(self):
        self.ready()
        isolated_skill = self.output / "isolated-skill"
        isolated_script = isolated_skill / "scripts" / "project_workflow.py"
        isolated_script.parent.mkdir(parents=True)
        isolated_script.write_bytes(SCRIPT.read_bytes())
        result = subprocess.run([sys.executable, "-B", str(isolated_script), "check", "--profile",
                                 str(self.profile_path), "--gate", "compile"], capture_output=True,
                                text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("rule catalog missing", " ".join(json.loads(result.stdout)["errors"]))

    def test_review_csv_cannot_be_redirected_outside_output(self):
        profile = self.ready()
        profile["review"]["inventory_path"] = "main.c"
        self.save(profile)
        before = (self.root / "main.c").read_bytes()
        result = self.cli("snapshot", "--profile", self.profile_path)
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.root / "main.c").read_bytes(), before)

    def approve_current_plan(self, profile):
        digest = self.api().approval_digest(profile)
        for row in profile["approvals"]:
            row["input_digest"] = digest
        self.save(profile)
        return digest

    def render_current_profile(self):
        target = self.output / "framework-review.html"
        result = subprocess.run([sys.executable, "-B", str(SKILL / "scripts" / "render_review.py"),
                                 "--profile", str(self.profile_path), "--output", str(target)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        return target.read_text(encoding="utf-8")

    def test_rendered_relative_diagram_bytes_are_bound_to_the_approved_plan(self):
        profile = self.ready()
        image = self.output / "preview.png"
        image.write_bytes(PNG)
        profile["diagrams"] = [{"id": "architecture", "title": "Fixture diagram", "kind": "expected",
                                "path": "preview.png", "source": "Fixture design", "caption": "Fixture"}]
        approved = self.approve_current_plan(profile)
        self.assertIn(base64.b64encode(PNG).decode("ascii"), self.render_current_profile())
        self.assertTrue(self.check("implement")["ok"], self.check("implement"))
        image.write_bytes(PNG + b"different diagram bytes")
        self.assertIn(base64.b64encode(image.read_bytes()).decode("ascii"), self.render_current_profile())
        self.assertNotEqual(self.api().approval_digest(profile), approved)
        self.assert_rejected("implement")

    def test_waveform_file_bytes_are_resolved_relative_to_output(self):
        profile = self.ready()
        trace = self.output / "trace.csv"
        trace.write_text("time,value\n0,0\n1,1\n", encoding="utf-8")
        profile["waveforms"] = [{"id": "wave", "title": "Fixture expected trace", "kind": "expected",
                                 "path": "trace.csv", "source": "Fixture design", "unit": "ms",
                                 "signals": [{"name": "fixture", "samples": [{"t": 0, "value": 0}, {"t": 1, "value": 1}]}]}]
        approved = self.approve_current_plan(profile)
        self.assertIn("data:image/svg+xml;base64,", self.render_current_profile())
        self.assertTrue(self.check("implement")["ok"])
        trace.write_text("time,value\n0,1\n1,0\n", encoding="utf-8")
        self.assertNotEqual(self.api().approval_digest(profile), approved)
        self.assert_rejected("implement")

    def test_registered_graph_files_must_exist(self):
        profile = self.ready()
        for key in ("diagrams", "waveforms"):
            with self.subTest(key=key):
                candidate = json.loads(json.dumps(profile))
                candidate[key] = [{"id": "missing", "path": "missing.png"}]
                with self.assertRaises(ValueError):
                    self.api().approval_digest(candidate)

    def test_graph_paths_must_stay_relative_and_inside_output(self):
        profile = self.ready()
        image = self.root / "outside.png"
        image.write_bytes(PNG)
        for value in ("../outside.png", str(image), "missing.png"):
            with self.subTest(path=value):
                profile["diagrams"] = [{"id": "outside", "path": value}]
                with self.assertRaises(ValueError):
                    self.api().approval_digest(profile)

    def test_profile_location_must_match_declared_output_directory(self):
        self.ready()
        copied = self.root / "copied-profile.json"
        copied.write_bytes(self.profile_path.read_bytes())
        self.assertFalse(self.api().check_profile(copied, "implement")["ok"])
        result = self.cli("snapshot", "--profile", copied)
        self.assertEqual(result.returncode, 2, result.stdout)

    def test_rule_body_change_invalidates_coverage_without_changing_plan_approval(self):
        profile = self.ready()
        isolated_skill = self.output / "isolated-rule-skill"
        catalog_path = SKILL / "assets" / "rule-catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
        (isolated_skill / "assets").mkdir(parents=True)
        (isolated_skill / "assets" / "rule-catalog.json").write_bytes(catalog_path.read_bytes())
        for relative in {rule["document"] for rule in catalog}:
            target = isolated_skill / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((SKILL / relative).read_bytes())
        api = self.api()
        api.SKILL_ROOT = isolated_skill
        self.assertTrue(api.check_profile(self.profile_path, "compile")["ok"])
        approved = api.approval_digest(profile)
        current = api.input_digest(profile)
        changed = isolated_skill / catalog[0]["document"]
        changed.write_bytes(changed.read_bytes() + b"\nAdditional mandatory fixture requirement.\n")
        result = api.check_profile(self.profile_path, "compile")
        self.assertFalse(result["ok"], result)
        self.assertEqual(api.approval_digest(profile), approved)
        self.assertEqual(api.input_digest(profile), current)
        api.snapshot(self.profile_path)
        rows = read_csv(self.root / profile["review"]["rule_coverage_path"])
        changed_ids = {rule["id"] for rule in catalog if rule["document"] == catalog[0]["document"]}
        self.assertEqual({row["status"] for row in rows if row["id"] in changed_ids}, {"pending"})
        self.assertEqual({row["status"] for row in rows if row["id"] not in changed_ids}, {"passed"})

    def test_missing_project_logs_block_compile_and_later_but_not_implementation(self):
        self.ready()
        (self.root / "Log" / "版本记录.md").unlink()
        (self.root / "Log" / "提示词记录.md").unlink()
        self.assertTrue(self.check("implement")["ok"])
        for gate in ("compile", "flash", "debug"):
            with self.subTest(gate=gate):
                self.assert_rejected(gate)

    def test_empty_project_logs_are_not_records(self):
        self.ready()
        for name in ("版本记录.md", "提示词记录.md"):
            (self.root / "Log" / name).write_text(" \n\t", encoding="utf-8")
        self.assert_rejected("compile")

    def test_project_log_headings_and_blank_labels_are_not_filled_records(self):
        self.ready()
        (self.root / "Log" / "版本记录.md").write_text(
            "# 版本记录\n\n版本号：\n修改日期：\n修改涉及文件：\n修改内容或者功能：\n", encoding="utf-8")
        (self.root / "Log" / "提示词记录.md").write_text("# 提示词记录\n", encoding="utf-8")
        self.assert_rejected("compile")

    def test_project_log_missing_required_field_is_rejected(self):
        self.ready()
        path = self.root / "Log" / "提示词记录.md"
        path.write_text("提示词时间：2026-10-27\n精简提示词内容：Fixture request\n", encoding="utf-8")
        self.assert_rejected("compile")


if __name__ == "__main__":
    unittest.main()
