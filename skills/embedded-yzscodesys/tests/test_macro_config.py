"""Compile and run the shipped public C/C++ headers with the real host tools."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HEADERS = ROOT / "assets" / "headers"


def find_compiler(variable, name, windows_fallback):
    configured = os.environ.get(variable)
    located = shutil.which(configured or name)
    if located:
        return Path(located)
    fallback = Path(windows_fallback)
    return fallback if not configured and fallback.is_file() else None


GCC = find_compiler("CC", "gcc", "C:/Strawberry/c/bin/gcc.exe")
GPP = find_compiler("CXX", "g++", "C:/Strawberry/c/bin/g++.exe")
ABI = ["PJ_ENABLE_ABI_VIEWS=1", "PJ_ABI_BYTE_ORDER=1234", "PJ_ABI_BITFIELD_ORDER=1234"]


class MacroConfigTests(unittest.TestCase):
    def setUp(self):
        if GCC is None or GPP is None:
            self.skipTest("Native C/C++ compilers unavailable: set CC/CXX executable paths; compile checks were not executed")
        self.temp = tempfile.TemporaryDirectory(prefix="macro-test-", dir=ROOT / "tests")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def compile(self, body, *, cpp=False, defines=(), success=True, standard=None, run=True):
        self.assertTrue((HEADERS / "Pj_MacroCfg.h").is_file(), "public configuration header is not implemented")
        source = self.directory / ("case.cpp" if cpp else "case.c")
        executable = self.directory / "case.exe"
        source.write_text('#include "Pj_MacroCfg.h"\n#include <assert.h>\n' + body, encoding="utf-8")
        command = [str(GPP if cpp else GCC), "-std=" + (standard or ("c++11" if cpp else "c99")), "-Wall", "-Wextra", "-Wconversion", "-Wsign-conversion", "-Werror", "-pedantic-errors", "-O2", "-I", str(HEADERS)]
        command += ["-D" + define for define in defines]
        command += [str(source), "-o", str(executable)]
        environment = dict(os.environ)
        environment["PATH"] = str(GCC.parent) + os.pathsep + str(GPP.parent) + os.pathsep + environment.get("PATH", "")
        compiled = subprocess.run(command, capture_output=True, text=True, errors="replace", env=environment, timeout=30)
        if success:
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            if run:
                executed = subprocess.run([str(executable)], capture_output=True, text=True, errors="replace", env=environment, timeout=30)
                self.assertEqual(executed.returncode, 0, executed.stdout + executed.stderr)
        else:
            self.assertNotEqual(compiled.returncode, 0, "unsafe or unavailable public interface unexpectedly compiled")
        return compiled

    def test_default_and_compatibility_alias_widths_and_signedness_in_c_and_cpp(self):
        body = r'''
int main(void)
{
    s8 S8_Val = (s8)-1;
    s16 S16_Val = (s16)-1;
    s32 S32_Val = (s32)-1;
    INT16S Old_S16 = (INT16S)-1;
    assert(PJ_HAS_U8 == 1);
    assert(sizeof(u8) * CHAR_BIT == 8);
    assert(sizeof(u16) * CHAR_BIT == 16);
    assert(sizeof(u32) * CHAR_BIT == 32);
    assert(sizeof(s8) * CHAR_BIT == 8 && S8_Val < 0);
    assert(sizeof(s16) * CHAR_BIT == 16 && S16_Val < 0);
    assert(sizeof(s32) * CHAR_BIT == 32 && S32_Val < 0);
    assert(sizeof(Uint8) * CHAR_BIT == 8 && sizeof(INT8U) * CHAR_BIT == 8);
    assert(sizeof(Uint16) * CHAR_BIT == 16 && sizeof(INT16U) * CHAR_BIT == 16);
    assert(sizeof(Uint32) * CHAR_BIT == 32 && sizeof(INT32U) * CHAR_BIT == 32);
    assert(Old_S16 < 0);
    return 0;
}
'''
        for cpp in (False, True):
            with self.subTest(cpp=cpp):
                self.compile(body, cpp=cpp)

    def test_bit_31_side_effects_and_if_else_use_are_safe(self):
        body = r'''
int main(void)
{
    u32 Dat_Buf[2] = {UINT32_C(0), UINT32_C(0x80000000)};
    unsigned int Dat_Pos = 0U;
    unsigned int Bit_Pos = 31U;
    unsigned int Bit_Val;
    set_bit(Dat_Buf[Dat_Pos++], Bit_Pos++);
    assert(Dat_Pos == 1U && Bit_Pos == 32U);
    assert(Dat_Buf[0] == UINT32_C(0x80000000));
    Dat_Pos = 0U;
    Bit_Pos = 31U;
    clr_bit(Dat_Buf[Dat_Pos++], Bit_Pos++);
    assert(Dat_Pos == 1U && Bit_Pos == 32U && Dat_Buf[0] == 0U);
    Dat_Pos = 1U;
    Bit_Pos = 31U;
    Bit_Val = get_bit(Dat_Buf[Dat_Pos++], Bit_Pos++);
    assert(Dat_Pos == 2U && Bit_Pos == 32U && Bit_Val == 1U);
    if (Dat_Buf[0] == 0U)
        set_bit(Dat_Buf[0], 1U);
    else
        set_bit(Dat_Buf[0], 0U);
    if (Dat_Buf[0] == 2U)
        clr_bit(Dat_Buf[0], 1U);
    else
        set_bit(Dat_Buf[0], 0U);
    assert(Dat_Buf[0] == 0U);
    return 0;
}
'''
        for cpp in (False, True):
            with self.subTest(cpp=cpp):
                self.compile(body, cpp=cpp)

    def test_invalid_compatibility_indices_do_not_shift_or_modify(self):
        body = r'''
int main(void)
{
    u8 Byte_Val = (u8)0xA5;
    u16 Half_Val = UINT16_C(0xA55A);
    u32 Word_Val = UINT32_C(0xA55AA55A);
    set_bit(Byte_Val, 8U);
    clr_bit(Byte_Val, -1);
    set_bit(Half_Val, 16U);
    clr_bit(Half_Val, UINTMAX_MAX);
    set_bit(Word_Val, 32U);
    clr_bit(Word_Val, -1);
    assert(Byte_Val == (u8)0xA5);
    assert(Half_Val == UINT16_C(0xA55A));
    assert(Word_Val == UINT32_C(0xA55AA55A));
    assert(get_bit(Word_Val, 32U) == 0U);
    assert(get_bit(Word_Val, -1) == 0U);
    assert(get_bit(Byte_Val, 8U) == 0U);
    return 0;
}
'''
        self.compile(body)
        self.compile(body, cpp=True)

    def test_checked_helpers_report_errors_and_preserve_outputs_on_failure(self):
        self.compile(r'''
int main(void)
{
    uintmax_t Mask_Val = UINTMAX_C(0xA5);
    unsigned int Bit_Val = 9U;
    assert(Pj_Bit_Mask_Checked(UINTMAX_C(32), 32U, &Mask_Val) == Bit_Index_Out_Of_Range);
    assert(Mask_Val == UINTMAX_C(0xA5));
    assert(Pj_Bit_Mask_Checked(UINTMAX_MAX, 32U, &Mask_Val) == Bit_Index_Out_Of_Range);
    assert(Pj_Bit_Mask_Checked(UINTMAX_C(0), 0U, &Mask_Val) == Bit_Width_Invalid);
    assert(Pj_Bit_Mask_Checked(UINTMAX_C(0), 33U, &Mask_Val) == Bit_Width_Invalid);
    assert(Pj_Bit_Mask_Checked(UINTMAX_C(0), sizeof(uintmax_t) * CHAR_BIT + 1U, &Mask_Val) == Bit_Width_Invalid);
    assert(Pj_Bit_Mask_Checked(UINTMAX_C(0), 32U, NULL) == Bit_Null_Output);
    assert(Pj_Bit_Mask_Checked(UINTMAX_C(31), 32U, &Mask_Val) == Bit_Ok);
    assert(Mask_Val == UINTMAX_C(0x80000000));
    assert(Pj_Bit_Get_Checked(UINTMAX_C(0x80000000), UINTMAX_C(31), 32U, &Bit_Val) == Bit_Ok);
    assert(Bit_Val == 1U);
    Bit_Val = 9U;
    assert(Pj_Bit_Get_Checked(UINTMAX_C(0), UINTMAX_C(32), 32U, &Bit_Val) == Bit_Index_Out_Of_Range);
    assert(Bit_Val == 9U);
    assert(Pj_Bit_Get_Checked(UINTMAX_C(0), UINTMAX_C(0), 32U, NULL) == Bit_Null_Output);
    return 0;
}
''')

    def test_safe_halfword_and_octet_extraction_do_not_use_union_layout(self):
        self.compile(r'''
int main(void)
{
    u32 Word_Val = UINT32_C(0x89ABCDEF);
    u8 Byte_Val = 0U;
    assert(Pj_U32_Lo_U16(Word_Val) == UINT16_C(0xCDEF));
    assert(Pj_U32_Hi_U16(Word_Val) == UINT16_C(0x89AB));
    assert(Pj_U32_From_U16(UINT16_C(0x89AB), UINT16_C(0xCDEF)) == Word_Val);
    assert(Pj_U32_Byte_Get_Checked(Word_Val, UINTMAX_C(0), &Byte_Val) == Bit_Ok && Byte_Val == (u8)0xEF);
    assert(Pj_U32_Byte_Get_Checked(Word_Val, UINTMAX_C(3), &Byte_Val) == Bit_Ok && Byte_Val == (u8)0x89);
    assert(Pj_U32_Byte_Get_Checked(Word_Val, UINTMAX_C(4), &Byte_Val) == Bit_Index_Out_Of_Range && Byte_Val == (u8)0x89);
    assert(Pj_U32_Byte_Get_Checked(Word_Val, UINTMAX_C(0), NULL) == Bit_Null_Output);
    return 0;
}
''')

    def test_nonportable_views_are_not_exposed_by_default(self):
        compiled = self.compile('#include "Pj_BitLayout.h"\nint main(void) { View_U32 Word_Val; (void)Word_Val; return 0; }\n', success=False)
        self.assertIn("View_U32", compiled.stderr)

    def test_opt_in_requires_explicit_byte_and_bitfield_abi(self):
        compiled = self.compile("int main(void) { return 0; }\n", defines=["PJ_ENABLE_ABI_VIEWS=1"], success=False)
        self.assertIn("PJ_ABI_BYTE_ORDER", compiled.stderr)
        self.assertIn("PJ_ABI_BITFIELD_ORDER", compiled.stderr)

    def test_host_c_opt_in_views_have_checked_size_and_observed_host_layout(self):
        self.compile(r'''
int main(void)
{
    View_U8 Byte_Val;
    View_U16 Half_Val;
    View_U32 Word_Val;
    assert(sizeof(Bit_U8) * CHAR_BIT == 8 && sizeof(View_U8) * CHAR_BIT == 8);
    assert(sizeof(Bit_U16) * CHAR_BIT == 16 && sizeof(View_U16) * CHAR_BIT == 16);
    assert(sizeof(Bit_U32) * CHAR_BIT == 32 && sizeof(View_U32) * CHAR_BIT == 32);
    Byte_Val.U8_Val = (u8)0x80;
    assert(Byte_Val.Bits_Dat.Bit_7 == 1U && Byte_Val.Bits_Dat.Bit_0 == 0U);
    Byte_Val.S8_Val = (s8)-1;
    assert(Byte_Val.S8_Val < 0);
    Half_Val.U16_Val = UINT16_C(0xABCD);
    assert(Half_Val.Bytes_Dat.Byte_0 == (u8)0xCD && Half_Val.Bytes_Dat.Byte_1 == (u8)0xAB);
    Word_Val.U32_Val = UINT32_C(0x89ABCDEF);
    assert(Word_Val.Half_Dat.Lo16_Val == UINT16_C(0xCDEF));
    assert(Word_Val.Half_Dat.Hi16_Val == UINT16_C(0x89AB));
    assert(Word_Val.Byte_Dat[0] == (u8)0xEF && Word_Val.Bytes_Dat.Byte_3 == (u8)0x89);
    assert(Word_Val.Bits_Dat.Bit_31 == 1U);
    return 0;
}
''', defines=ABI)

    def test_cpp_opt_in_compiles_without_cross_member_reinterpretation(self):
        self.compile(r'''
int main(void)
{
    View_U8 Byte_Val = {};
    View_U16 Half_Val = {};
    View_U32 Word_Val = {};
    Word_Val.U32_Val = UINT32_C(0x80000000);
    assert(Word_Val.U32_Val == UINT32_C(0x80000000));
    Half_Val.U16_Val = UINT16_C(0x8000);
    assert(Half_Val.U16_Val == UINT16_C(0x8000));
    Byte_Val.S8_Val = (s8)-1;
    assert(Byte_Val.S8_Val < 0);
    assert(sizeof(Bit_U8) * CHAR_BIT == 8 && sizeof(Bit_U32) * CHAR_BIT == 32);
    return 0;
}
''', cpp=True, defines=ABI)

    def test_disabled_u8_branch_retains_real_16_and_32_bit_support(self):
        self.compile(r'''
int main(void)
{
    u16 Half_Val = 0U;
    u32 Word_Val = 0U;
    assert(PJ_HAS_U8 == 0);
    set_bit(Half_Val, 15U);
    set_bit(Word_Val, 31U);
    assert(Half_Val == UINT16_C(0x8000) && Word_Val == UINT32_C(0x80000000));
    return 0;
}
''', defines=["PJ_DISABLE_U8=1"])
        compiled = self.compile("int main(void) { u8 Byte_Val = 0; return (int)Byte_Val; }\n", defines=["PJ_DISABLE_U8=1"], success=False)
        self.assertIn("u8", compiled.stderr)
        self.compile("int main(void) { View_U16 Half_Val; View_U32 Word_Val; (void)Half_Val; (void)Word_Val; return 0; }\n", defines=ABI + ["PJ_DISABLE_U8=1"])

    def test_requiring_unavailable_u8_reports_the_missing_capability(self):
        compiled = self.compile("int main(void) { return 0; }\n", defines=["PJ_DISABLE_U8=1", "PJ_REQUIRE_U8=1"], success=False)
        self.assertIn("PJ_REQUIRE_U8", compiled.stderr)

    def test_compatibility_aliases_can_be_disabled_for_vendor_ownership(self):
        self.compile(r'''
typedef struct Vendor_Uint16
{
    u16 Raw_Val;
} Uint16;
int main(void)
{
    Uint16 Vendor_Val = {UINT16_C(7)};
    u16 Dat_Val = Vendor_Val.Raw_Val;
    assert(Dat_Val == UINT16_C(7));
    return 0;
}
''', defines=["PJ_ENABLE_COMPAT_ALIASES=0"])

    def test_c90_is_rejected_with_a_clear_porting_requirement(self):
        compiled = self.compile("int main(void) { return 0; }\n", standard="c90", success=False)
        self.assertIn("C99", compiled.stderr)


if __name__ == "__main__":
    unittest.main()
