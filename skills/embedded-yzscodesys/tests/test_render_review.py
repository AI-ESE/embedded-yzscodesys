"""Behavior tests for the standalone offline review CLI (stdlib only)."""
import base64
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "render_review.py"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/l9sAAAAASUVORK5CYII=")


class ReviewDocument(HTMLParser):
    def __init__(self, content):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.elements = []
        self.noncontent = 0
        self.feed(content)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))
        if tag in ("script", "style"):
            self.noncontent += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.noncontent -= 1

    def handle_data(self, data):
        if not self.noncontent:
            self.text.append(data)

    @property
    def words(self):
        return " ".join(self.text)

    def attrs(self, tag):
        return [attrs for found, attrs in self.elements if found == tag]


class RenderReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="审核资料-", dir=SCRIPT.parents[1] / "tests")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = self.root / "工程资料.json"
        self.output = self.root / "审核报告.html"

    def render(self, profile):
        self.profile.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--profile", str(self.profile), "--output", str(self.output)],
            capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        content = self.output.read_text(encoding="utf-8")
        return content, ReviewDocument(content)

    def test_empty_profile_leaves_five_review_stages_unconfirmed(self):
        _, document = self.render({})
        stages = [attrs.get("id") for attrs in document.attrs("details")]
        self.assertTrue({"A1", "A2", "A3", "A4", "A5"}.issubset(stages))
        self.assertIn("待提供", document.words)
        self.assertIn("用户意见", document.words)
        self.assertIn("方案版本", document.words)
        self.assertIn("设计框架", document.words)
        self.assertIn("C1", document.words)
        self.assertIn("L3", document.words)
        self.assertNotIn("STM32", document.words)
        selected = [attrs.get("value") for attrs in document.attrs("option") if "selected" in attrs]
        self.assertEqual(selected, ["待确认"] * 5)
        self.assertIn("不代表已取得用户授权", document.words)

    def test_empty_architecture_names_the_required_resource_and_initialization_fields(self):
        _, document = self.render({})
        for field in ("任务栈", "运行预算", "同步 / 通知", "数据所有者", "执行顺序", "失败处理"):
            self.assertIn(field, document.words)

    def test_enabled_ui_shows_screen_assets_memory_and_page_review_records(self):
        _, document = self.render({'architecture': {'ui': {
            'enabled': True, 'screen': {'driver_chip': 'Fixture_Display_Driver'},
            'resources': {'flash_total_bytes': '待提供', 'ram_total_bytes': '待提供'},
            'assets': [{'id': 'Logo_Asset', 'category': 'Logo', 'flash_bytes': '待分析', 'ram_peak_bytes': '待分析'}],
            'pages': [{'id': 'Fixture_Page'}]
        }}, 'review': {'ui_pages': [{'id': 'Fixture_Page', 'rounds': [{'round': 'U1', 'evidence': 'Round_Proof', 'status': 'pending'}]}]}})
        for text in ('UI资源与逐页审核', 'Fixture_Display_Driver', 'Logo_Asset', 'Fixture_Page', 'Round_Proof', 'Flash', 'RAM', '92%'):
            self.assertIn(text, document.words)

    def test_non_ui_project_does_not_request_screen_resources(self):
        _, document = self.render({'architecture': {'ui': {'enabled': False}}})
        self.assertNotIn('UI资源与逐页审核', document.words)

    def test_blank_document_registration_stays_in_missing_material_summary(self):
        _, document = self.render({"documents": [{"id": "datasheet", "path": "", "version": "", "sha256": "", "status": "pending"}]})
        self.assertIn("规格书 / 原理图及版本", document.words)

    def test_untrusted_text_and_script_end_are_rendered_as_text(self):
        attack = '</script><script>alert("审核")</script><img src=x onerror=alert(1)>'
        _, document = self.render({"project_name": attack, "revision": "版本'\"<一>", "pins": [{"id": attack, "source": attack}]})
        self.assertIn(attack, document.words)
        self.assertEqual(len(document.attrs("script")), 1)
        self.assertFalse(document.attrs("img"))
        for _, attrs in document.elements:
            self.assertFalse(any(name.lower().startswith("on") for name in attrs))

    def test_embedded_raster_and_zoom_survive_moving_html(self):
        image = self.root / "电平预览.png"
        image.write_bytes(PNG)
        _, document = self.render({"diagrams": [{"title": "实际资料图", "kind": "expected", "path": image.name}]})
        urls = [attrs["src"] for attrs in document.attrs("img")]
        self.assertEqual(len(urls), 1)
        self.assertEqual(base64.b64decode(urls[0].split(",", 1)[1]), PNG)
        self.assertIn(urls[0], [attrs.get("href") for attrs in document.attrs("a")])
        relocated = self.root / "移动后" / "独立.html"
        relocated.parent.mkdir()
        shutil.copyfile(self.output, relocated)
        image.unlink()
        self.profile.unlink()
        moved = ReviewDocument(relocated.read_text(encoding="utf-8"))
        self.assertEqual([attrs["src"] for attrs in moved.attrs("img")], urls)
        self.assertTrue(all(not attrs.get("src", "").startswith(("http:", "https:", "file:")) for _, attrs in moved.elements))

    def test_unsafe_and_fake_image_files_are_not_embedded(self):
        (self.root / "脚本.svg").write_text('<svg onload="alert(1)"></svg>', encoding="utf-8")
        (self.root / "伪装.png").write_text('<svg onload="alert(1)"></svg>', encoding="utf-8")
        paths = ["../private.png", "https://evil.invalid/x.png", "脚本.svg", "伪装.png", "data:image/png;base64,AAAA", "missing.png"]
        _, document = self.render({"diagrams": [{"path": path, "kind": "expected"} for path in paths]})
        self.assertFalse(document.attrs("img"))
        self.assertGreaterEqual(document.words.count("未嵌入"), len(paths))

    def test_waveforms_keep_expected_simulation_and_measurement_distinct(self):
        samples = [{"t": 0, "value": 0}, {"t": 2, "value": 1}, {"t": 3, "value": 0}]
        self.root.joinpath("采集.csv").write_text("t,value\n0,0\n2,1\n3,0\n", encoding="utf-8")
        records = [
            {"id": "w1", "title": "预期使能", "kind": "expected", "unit": "us", "signals": [{"name": "EN", "samples": samples}]},
            {"id": "w2", "title": "模型输出", "kind": "simulation", "unit": "ms", "source": "模型v1", "signals": [{"name": "CLK", "samples": samples}]},
            {"id": "w3", "title": "测量缺证", "kind": "measured", "unit": "us", "signals": [{"name": "IRQ", "samples": samples}]},
            {"id": "w4", "title": "测量资料", "kind": "measured", "unit": "us", "source": "采集记录", "path": "采集.csv", "instrument": "示波器", "conditions": "条件记录", "signals": [{"name": "RESET", "samples": samples}]},
            {"id": "w5", "title": "单位缺失", "kind": "expected", "signals": [{"name": "CS", "samples": samples}]},
        ]
        _, document = self.render({"waveforms": records})
        self.assertIn("设计预期／待确认", document.words)
        self.assertIn("仿真／待审核", document.words)
        self.assertIn("实测证据待补", document.words)
        self.assertIn("实测资料／待审核", document.words)
        self.assertIn("时间单位或有效采样数据待补", document.words)
        self.assertNotIn("实测成功", document.words)
        self.assertEqual(len(document.attrs("img")), 4)
        for attrs in document.attrs("img"):
            svg = base64.b64decode(attrs["src"].split(",", 1)[1]).decode("utf-8")
            self.assertIn("时间 (", svg)
            self.assertIn("polyline", svg)

    def test_csv_reviews_and_build_hardware_records_are_readable(self):
        with self.root.joinpath("逐文件.csv").open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(["path", "C1", "C2", "C3"])
            writer.writerow(["源码/电机.c", "待检查", "未执行", "未执行"])
        _, document = self.render({
            "review": {"inventory_path": "逐文件.csv"},
            "build": {"status": "待构建", "optimization": "-O2", "exit_code": 0},
            "hardware": {"status": "待烧录", "debug": {"connection": "待接线"}},
            "architecture": {"initialization": [{"step": "保护输出先置安全态"}], "tasks": [{"name": "监控任务", "period": "待确认"}]},
        })
        for expected in ("源码/电机.c", "未执行", "-O2", "待烧录", "待接线", "保护输出先置安全态", "监控任务"):
            self.assertIn(expected, document.words)

    def test_unsubstantiated_approval_does_not_become_confirmation(self):
        _, document = self.render({"revision": "R2", "approvals": [{"stage": "A1", "status": "已确认", "revision": "R1"}]})
        stages = [attrs for attrs in document.attrs("details") if attrs.get("id") == "A1"]
        self.assertEqual(stages[0].get("data-status"), "待确认")
        self.assertIn("证据或版本待核对", document.words)

    def test_pending_schema_status_is_presented_as_pending_in_chinese(self):
        _, document = self.render({"approvals": [{"stage": "A1", "status": "pending"}]})
        stage = next(attrs for attrs in document.attrs("details") if attrs.get("id") == "A1")
        self.assertEqual(stage["data-status"], "待确认")

    def test_current_evidenced_approval_is_only_displayed_without_altering_input(self):
        evidence = "用户明确确认 A1，资料版本 R2，范围为所列平台资料。"
        profile = {"revision": "R2", "approvals": [{"stage": "A1", "status": "已确认", "revision": "R2", "approval_digest": "a" * 64, "user_evidence_text": evidence, "user_evidence_sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest()}]}
        _, document = self.render(profile)
        stage = next(attrs for attrs in document.attrs("details") if attrs.get("id") == "A1")
        self.assertEqual(stage["data-status"], "记录已确认")
        self.assertEqual(json.loads(self.profile.read_text(encoding="utf-8")), profile)
        self.assertIn("摘要仍由 check 准入脚本核验", document.words)
        self.assertEqual([attrs.get("value") for attrs in document.attrs("option") if "selected" in attrs], ["待确认"] * 5)

    def test_approval_evidence_file_hash_is_checked_instead_of_path_text(self):
        evidence = self.root / "用户确认.txt"
        evidence.write_text("用户明确确认当前 A1 方案范围。", encoding="utf-8")
        approval = {"stage": "A1", "status": "confirmed", "revision": "R1", "input_digest": "a" * 64, "user_evidence": evidence.name, "user_evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest()}
        _, document = self.render({"revision": "R1", "approvals": [approval]})
        stage = next(attrs for attrs in document.attrs("details") if attrs.get("id") == "A1")
        self.assertEqual(stage["data-status"], "记录已确认")
        evidence.write_text("已被修改的证据", encoding="utf-8")
        _, changed = self.render({"revision": "R1", "approvals": [approval]})
        stage = next(attrs for attrs in changed.attrs("details") if attrs.get("id") == "A1")
        self.assertEqual(stage["data-status"], "待确认")

    def test_workflow_csv_paths_resolve_inside_profile_directory(self):
        project = self.root / "工程"
        output = project / "审核"
        output.mkdir(parents=True)
        inventory = output / "review-files.csv"
        inventory.write_text("path,C1\nsrc/真实.c,未执行\n", encoding="utf-8")
        self.profile = output / "project-profile.json"
        for path in ("审核/review-files.csv", str(inventory)):
            with self.subTest(path=path):
                _, document = self.render({"project_root": str(project), "output_dir": str(output), "review": {"inventory_path": path}})
                self.assertIn("src/真实.c", document.words)

    def test_existing_outside_image_and_csv_are_not_read(self):
        outside = self.root.parent / (self.root.name + "-outside")
        outside.mkdir()
        self.addCleanup(shutil.rmtree, outside)
        outside.joinpath("outside.png").write_bytes(PNG)
        outside.joinpath("outside.csv").write_text("secret\nprivate-contents-8941\n", encoding="utf-8")
        prefix = "../" + outside.name
        _, document = self.render({"diagrams": [{"path": prefix + "/outside.png"}], "review": {"inventory_path": prefix + "/outside.csv"}})
        self.assertFalse(document.attrs("img"))
        self.assertNotIn("private-contents-8941", document.words)
        self.assertIn("仅允许资料目录内的相对文件路径", document.words)

    def test_waveform_extreme_or_invalid_samples_remain_unrendered(self):
        invalids = [
            [{"t": 0, "value": 0}, {"t": 10 ** 500, "value": 1}],
            [{"t": 0, "value": 0}, {"t": 0, "value": 1}],
            [{"t": 0, "value": 0}, {"t": 1, "value": 2}],
            [{"t": "0", "value": 0}, {"t": 1, "value": 1}],
        ]
        _, document = self.render({"waveforms": [{"kind": "expected", "unit": "us", "signals": [{"name": "signal", "samples": samples}]} for samples in invalids]})
        self.assertFalse(document.attrs("img"))
        self.assertEqual(document.words.count("未嵌入"), 4)

    def test_waveform_labels_cannot_insert_svg_markup(self):
        attack = '</text><script>alert(1)</script><text>'
        _, document = self.render({"waveforms": [{"title": attack, "kind": "expected", "unit": "us", "signals": [{"name": attack, "samples": [{"t": 0, "value": 0}, {"t": 1, "value": 1}]}]}]})
        self.assertEqual(len(document.attrs("img")), 1)
        xml = ET.fromstring(base64.b64decode(document.attrs("img")[0]["src"].split(",", 1)[1]))
        self.assertFalse(xml.findall(".//{http://www.w3.org/2000/svg}script"))
        self.assertIn(attack, " ".join(xml.itertext()))

    def test_malformed_optional_sections_do_not_turn_into_success(self):
        _, document = self.render({"mcu": [], "architecture": {"tasks": "待定义"}, "pins": [None], "build": 0, "hardware": "待接线", "approvals": [{"stage": "A1", "status": ["已确认"]}]})
        self.assertIn("待定义", document.words)
        self.assertIn("待接线", document.words)
        self.assertNotIn("记录已确认", document.words)

    def test_invalid_json_fails_without_creating_report(self):
        self.profile.write_text("{not JSON", encoding="utf-8")
        result = subprocess.run([sys.executable, "-B", str(SCRIPT), "--profile", str(self.profile), "--output", str(self.output)], capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())
        self.assertIn("JSON", result.stderr)


if __name__ == "__main__":
    unittest.main()
