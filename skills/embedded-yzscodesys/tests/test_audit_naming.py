import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'audit_naming.py'


class NamingTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SCRIPT.is_file(), 'portable naming auditor is not implemented')
        spec = importlib.util.spec_from_file_location('naming_under_test', SCRIPT)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def audit(self, source, **kwargs):
        (self.root / 'sample.c').write_text(source, encoding='utf-8-sig')
        return self.module.audit_project(self.root, **kwargs)

    def test_pascal_underscore_parameters_and_struct_members(self):
        result = self.audit('struct Sample_Dat { unsigned int Input_Vol; unsigned int Ready_Flg : 1; };\n'
                            'void FML_Sample_Read(struct Sample_Dat *Sample_Dat, unsigned int Sample_Count) { unsigned int LocalValue; }')
        self.assertEqual(result['findings'], [])
        self.assertGreater(result['summary']['functions'], 0)

    def test_parameter_without_underscore_is_reported_but_local_is_not(self):
        result = self.audit('void FML_Sample_Read(unsigned int InputVol) { unsigned int LocalValue; }')
        self.assertIn('InputVol', [x['name'] for x in result['findings']])
        self.assertNotIn('LocalValue', [x['name'] for x in result['findings']])

    def test_explicit_abbreviations_override_full_words(self):
        result = self.audit('void FML_Sample_Read(unsigned int Input_Voltage, char *Data_Buffer);')
        names = {x['name'] for x in result['findings']}
        self.assertIn('Input_Voltage', names)
        self.assertIn('Data_Buffer', names)

    def test_struct_type_member_and_object_categories_are_checked(self):
        result = self.audit('struct SampleData { unsigned int input_voltage; };\nstruct SampleData LocalData;')
        names = {x['name'] for x in result['findings']}
        self.assertTrue({'SampleData', 'input_voltage', 'LocalData'} <= names)

    def test_charge_and_target_abbreviations_are_preferences(self):
        result = self.audit('void FML_Charge_Set(unsigned int Target_Vol);')
        self.assertEqual(result['findings'], [])
        suggestions = ' '.join(row['message'] for row in result['suggestions'])
        self.assertIn('Charge -> Chg', suggestions)
        self.assertIn('Target -> Tag', suggestions)

    def test_comments_strings_and_calls_are_not_declarations(self):
        result = self.audit('/* struct BadName { int BadField; }; */\n'
                            'void FML_Sample_Run(void) { const char *Text = "Voltage Data Buffer";\n FML_Sample_Set(InputVol); }')
        self.assertEqual(result['findings'], [])

    def test_array_and_callback_parameters(self):
        result = self.audit('void FML_Sample_Read(char Dat_Buf[16], void (*Done_Cb)(unsigned int Result_Code));')
        self.assertEqual(result['findings'], [])

    def test_numeric_bit_member_segments_are_allowed(self):
        result = self.audit('struct Bit_U8 { unsigned int Bit_0 : 1; unsigned int Bit_7 : 1; };')
        self.assertEqual(result['findings'], [])

    def test_vendor_scope_is_explicit_and_not_rewritten(self):
        vendor = self.root / 'sdk'
        vendor.mkdir()
        text = 'struct VendorData { unsigned int voltage; };'
        (vendor / 'vendor.h').write_text(text, encoding='utf-8')
        result = self.audit('void FML_Sample_Run(void) {}', vendor_roots=[vendor])
        self.assertEqual(result['findings'], [])
        self.assertEqual((vendor / 'vendor.h').read_text(), text)

    def test_empty_project_is_not_a_clean_review(self):
        result = self.module.audit_project(self.root)
        self.assertTrue(result['manual'])


if __name__ == '__main__':
    unittest.main()
