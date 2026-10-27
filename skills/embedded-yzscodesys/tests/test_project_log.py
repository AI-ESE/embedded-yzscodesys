import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/project_log.py'


class ProjectLogTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'project log helper is not implemented')
        spec = importlib.util.spec_from_file_location('project_log_under_test', SCRIPT)
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_initialize_creates_exact_two_markdown_files_and_preserves_existing(self):
        self.api.initialize(self.root)
        self.assertEqual({p.name for p in (self.root/'Log').iterdir()}, {'版本记录.md', '提示词记录.md'})
        old = self.root/'Log/版本记录.md'
        old.write_text('已有历史\n', encoding='utf-8')
        self.api.initialize(self.root)
        self.assertEqual(old.read_text(encoding='utf-8'), '已有历史\n')

    def test_version_records_append_in_order_with_required_fields(self):
        self.api.append_version(self.root, 'v1', '2026-10-27', ['APP/APP_Chg.c'], '增加状态检查')
        before = (self.root/'Log/版本记录.md').read_bytes()
        self.api.append_version(self.root, 'v2', '2026-10-28', ['APP/APP_Chg.c', 'Task/Task_Main.c'], '修正故障恢复')
        content = (self.root/'Log/版本记录.md').read_bytes()
        self.assertTrue(content.startswith(before + b'\n\n'))
        text = content.decode('utf-8')
        for field in ('版本号：v1', '修改日期：2026-10-27', '修改涉及文件：', '修改内容或者功能：', '版本号：v2', '修正故障恢复'):
            self.assertIn(field, text)
        self.assertLess(text.index('版本号：v1'), text.index('版本号：v2'))

    def test_prompt_records_append_every_question_summary_and_actual_result(self):
        self.api.append_prompt(self.root, '2026-10-27T12:00:00+08:00', '核对引脚', '发现极性冲突，待确认')
        before = (self.root/'Log/提示词记录.md').read_bytes()
        self.api.append_prompt(self.root, '2026-10-27T12:10:00+08:00', '修正反相链', '已改审核表，尚未烧录')
        content = (self.root/'Log/提示词记录.md').read_bytes()
        self.assertTrue(content.startswith(before + b'\n\n'))
        text = content.decode('utf-8')
        for field in ('提示词时间：', '精简提示词内容：', '最终改善输出：', '核对引脚', '尚未烧录'):
            self.assertIn(field, text)

    def test_append_preserves_existing_bom_and_history_bytes(self):
        self.api.initialize(self.root)
        old = self.root/'Log/提示词记录.md'
        history = b'\xef\xbb\xbf' + '旧记录\r\n'.encode('utf-8')
        old.write_bytes(history)
        self.api.append_prompt(self.root, '2026-10-27', '新问题', '分析结论')
        self.assertTrue(old.read_bytes().startswith(history))
        self.assertEqual(old.read_bytes().count(b'\xef\xbb\xbf'), 1)

    def test_invalid_empty_record_does_not_append(self):
        self.api.initialize(self.root)
        before = (self.root/'Log/提示词记录.md').read_bytes()
        with self.assertRaises(ValueError):
            self.api.append_prompt(self.root, '2026-10-27', '', '待处理')
        self.assertEqual((self.root/'Log/提示词记录.md').read_bytes(), before)

    def test_version_file_reference_cannot_escape_project(self):
        with self.assertRaises(ValueError):
            self.api.append_version(self.root, 'v1', '2026-10-27', ['../other/project.c'], '说明')
        self.assertFalse((self.root/'Log/版本记录.md').exists())

    def test_log_directory_file_collision_preserves_user_file(self):
        collision = self.root/'Log'
        collision.write_text('保留', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.api.initialize(self.root)
        self.assertEqual(collision.read_text(encoding='utf-8'), '保留')


if __name__ == '__main__':
    unittest.main()
