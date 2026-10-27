import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'package_skill.py'


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'portable packager is not implemented')
        spec = importlib.util.spec_from_file_location('package_under_test', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'test-skill'
        self.root.mkdir()
        (self.root / 'SKILL.md').write_text('---\nname: test-skill\ndescription: Use when testing a package.\n---\n[Guide](references/guide.md)\n', encoding='utf-8')
        (self.root / 'references').mkdir()
        (self.root / 'references/guide.md').write_text('# Guide\n', encoding='utf-8')

    def test_valid_folder_can_be_moved_and_packaged(self):
        output = self.root.parent / 'test-skill.zip'
        result = self.module.check_package(self.root)
        self.assertTrue(result['ok'], result)
        report = self.module.pack_skill(self.root, output)
        self.assertTrue(output.is_file())
        self.assertTrue(report['sha256'])
        with zipfile.ZipFile(output) as archive:
            self.assertIn('test-skill/SKILL.md', archive.namelist())
            extracted = self.root.parent / 'relocated'
            archive.extractall(extracted)
        self.assertTrue(self.module.check_package(extracted / 'test-skill')['ok'])

    def test_missing_relative_reference_blocks_release(self):
        (self.root / 'references/guide.md').unlink()
        self.assertFalse(self.module.check_package(self.root)['ok'])

    def test_path_outside_package_is_rejected(self):
        (self.root / 'references/guide.md').write_text('[Outside](../../outside.md)', encoding='utf-8')
        (self.root.parent / 'outside.md').write_text('external', encoding='utf-8')
        self.assertFalse(self.module.check_package(self.root)['ok'])

    def test_invalid_json_blocks_release(self):
        (self.root / 'assets').mkdir()
        (self.root / 'assets/profile.json').write_text('{broken', encoding='utf-8')
        self.assertFalse(self.module.check_package(self.root)['ok'])

    def test_generated_build_outputs_do_not_enter_distribution(self):
        generated = self.root / 'references/library/references/example-project/tests/layers/out'
        generated.mkdir(parents=True)
        (generated / 'test.exe').write_bytes(b'generated executable')
        (generated / 'test.c').write_text('generated source', encoding='utf-8')
        report = self.module.pack_skill(self.root, self.root.parent / 'clean.zip')
        self.assertTrue(report['ok'])
        with zipfile.ZipFile(self.root.parent / 'clean.zip') as archive:
            self.assertFalse(any('/out/' in name for name in archive.namelist()))

    def test_output_inside_skill_is_rejected(self):
        with self.assertRaises(ValueError):
            self.module.pack_skill(self.root, self.root / 'nested.zip')

    def test_existing_archive_is_not_overwritten(self):
        output = self.root.parent / 'test-skill.zip'
        output.write_bytes(b'preserve')
        with self.assertRaises(FileExistsError):
            self.module.pack_skill(self.root, output)
        self.assertEqual(output.read_bytes(), b'preserve')

    def test_distribution_version_is_preserved_in_manifest(self):
        import json
        (self.root / 'assets').mkdir()
        (self.root / 'assets/distribution.json').write_text('{"version":"1.1.0"}', encoding='utf-8')
        self.module.pack_skill(self.root, self.root.parent / 'versioned.zip')
        manifest = json.loads((self.root / 'package-manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], '1.1.0')

    def test_invalid_distribution_version_does_not_create_archive(self):
        (self.root / 'assets').mkdir()
        (self.root / 'assets/distribution.json').write_text('{"version":"../../bad"}', encoding='utf-8')
        output = self.root.parent / 'bad-version.zip'
        with self.assertRaises(ValueError):
            self.module.pack_skill(self.root, output)
        self.assertFalse(output.exists())

    def test_historical_absolute_links_are_explicit_not_required_for_runtime(self):
        archive = self.root / 'references/library/references/example-project'
        archive.mkdir(parents=True)
        (archive / 'history.md').write_text('[Historical source](F:/old/project.c:12)', encoding='utf-8')
        result = self.module.check_package(self.root)
        self.assertTrue(result['ok'], result)
        self.assertEqual(len(result['historical_external_links']), 1)


if __name__ == '__main__':
    unittest.main()
