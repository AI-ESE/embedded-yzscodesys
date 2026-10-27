/*
 * Public integer aliases and checked bit operations.
 * Destination after project/toolchain review: Common/Inc/Pj_MacroCfg.h.
 * C99 or C++11; no product parameters and no implicit register access.
 */
#ifndef PJ_MACROCFG_H
#define PJ_MACROCFG_H

#if defined(__cplusplus)
# if __cplusplus < 201103L
#  error "Pj_MacroCfg requires C++11 or later; port older toolchains explicitly."
# endif
#elif !defined(__STDC_VERSION__) || (__STDC_VERSION__ < 199901L)
# error "Pj_MacroCfg requires C99 or later with stdint.h and inline."
#endif

#include <limits.h>
#include <stddef.h>
#include <stdint.h>

#if !defined(UINT16_MAX) || !defined(INT16_MAX) || !defined(UINT32_MAX) || !defined(INT32_MAX)
# error "Exact 16-bit and 32-bit stdint types are required; supply a reviewed target adapter."
#endif

#ifndef PJ_DISABLE_U8
# define PJ_DISABLE_U8 0
#endif
#ifndef PJ_REQUIRE_U8
# define PJ_REQUIRE_U8 0
#endif
#ifndef PJ_ENABLE_COMPAT_ALIASES
# define PJ_ENABLE_COMPAT_ALIASES 1
#endif
#ifndef PJ_ENABLE_ABI_VIEWS
# define PJ_ENABLE_ABI_VIEWS 0
#endif

#if (PJ_DISABLE_U8 != 0) && (PJ_DISABLE_U8 != 1)
# error "PJ_DISABLE_U8 must be 0 or 1."
#endif
#if (PJ_ENABLE_COMPAT_ALIASES != 0) && (PJ_ENABLE_COMPAT_ALIASES != 1)
# error "PJ_ENABLE_COMPAT_ALIASES must be 0 or 1."
#endif
#if (PJ_ENABLE_ABI_VIEWS != 0) && (PJ_ENABLE_ABI_VIEWS != 1)
# error "PJ_ENABLE_ABI_VIEWS must be 0 or 1."
#endif

/* User-selected default aliases: prefer these six in new APIs. */
typedef uint32_t u32;
typedef uint16_t u16;
typedef int32_t s32;
typedef int16_t s16;

#if !PJ_DISABLE_U8 && (CHAR_BIT == 8) && defined(UINT8_MAX) && defined(INT8_MAX)
# define PJ_HAS_U8 1
typedef uint8_t u8;
typedef int8_t s8;
#else
# define PJ_HAS_U8 0
#endif

#if PJ_REQUIRE_U8 && !PJ_HAS_U8
# error "PJ_REQUIRE_U8: exact uint8_t/int8_t aliases are unavailable; do not substitute 16-bit types."
#endif

/* File-scope integer-constant checks also work in C99 (no C11 requirement). */
typedef char Pj_U16_Width_Check[(sizeof(u16) * CHAR_BIT == 16U) ? 1 : -1];
typedef char Pj_U32_Width_Check[(sizeof(u32) * CHAR_BIT == 32U) ? 1 : -1];
typedef char Pj_S16_Width_Check[(sizeof(s16) * CHAR_BIT == 16U) ? 1 : -1];
typedef char Pj_S32_Width_Check[(sizeof(s32) * CHAR_BIT == 32U) ? 1 : -1];
#if PJ_HAS_U8
typedef char Pj_U8_Width_Check[(sizeof(u8) * CHAR_BIT == 8U) ? 1 : -1];
typedef char Pj_S8_Width_Check[(sizeof(s8) * CHAR_BIT == 8U) ? 1 : -1];
#endif

/* Explicit user compatibility exceptions; turn off when an SDK owns these names. */
#if PJ_ENABLE_COMPAT_ALIASES
typedef u32 Uint32;
typedef u16 Uint16;
typedef u32 INT32U;
typedef u16 INT16U;
typedef s16 INT16S;
# if PJ_HAS_U8
typedef u8 Uint8;
typedef u8 INT8U;
# endif
#endif

typedef enum Bit_Result
{
    Bit_Ok = 0,
    Bit_Null_Output,
    Bit_Index_Out_Of_Range,
    Bit_Width_Invalid
} Bit_Result;

/* Logical widths 1..32 only; exact u32 guarantees that uintmax_t has these value bits.
 * Failure leaves *Mask_Out unchanged; negative integral indices convert out of range. */
static inline Bit_Result Pj_Bit_Mask_Checked(uintmax_t Bit_Pos,
                                            size_t Dat_Width,
                                            uintmax_t *Mask_Out)
{
    if (Mask_Out == NULL)
    {
        return Bit_Null_Output;
    }
    if ((Dat_Width == 0U) || (Dat_Width > 32U))
    {
        return Bit_Width_Invalid;
    }
    if (Bit_Pos >= (uintmax_t)Dat_Width)
    {
        return Bit_Index_Out_Of_Range;
    }
    *Mask_Out = UINTMAX_C(1) << Bit_Pos;
    return Bit_Ok;
}

static inline Bit_Result Pj_Bit_Get_Checked(uintmax_t Dat_Val,
                                           uintmax_t Bit_Pos,
                                           size_t Dat_Width,
                                           unsigned int *Bit_Out)
{
    uintmax_t Mask_Val = UINTMAX_C(0);
    Bit_Result Check_Val;
    if (Bit_Out == NULL)
    {
        return Bit_Null_Output;
    }
    Check_Val = Pj_Bit_Mask_Checked(Bit_Pos, Dat_Width, &Mask_Val);
    if (Check_Val != Bit_Ok)
    {
        return Check_Val;
    }
    *Bit_Out = ((Dat_Val & Mask_Val) != UINTMAX_C(0)) ? 1U : 0U;
    return Bit_Ok;
}

/*
 * Dat_Ptr MUST point to an actual u8/u16/u32 object (or identical alias),
 * not another same-sized base type, signed object, volatile register or bit-field.
 * Dat_Width MUST be sizeof(the actual object) * CHAR_BIT.
 * Exactly one typed read and one typed write on success. Not atomic.
 */
static inline Bit_Result Pj_Bit_Update_Checked(void *Dat_Ptr,
                                              uintmax_t Bit_Pos,
                                              size_t Dat_Width,
                                              unsigned int Set_Val)
{
    uintmax_t Mask_Val = UINTMAX_C(0);
    Bit_Result Check_Val;
    if (Dat_Ptr == NULL)
    {
        return Bit_Null_Output;
    }
    if ((Dat_Width != 16U) && (Dat_Width != 32U)
#if PJ_HAS_U8
        && (Dat_Width != 8U)
#endif
       )
    {
        return Bit_Width_Invalid;
    }
    Check_Val = Pj_Bit_Mask_Checked(Bit_Pos, Dat_Width, &Mask_Val);
    if (Check_Val != Bit_Ok)
    {
        return Check_Val;
    }
#if PJ_HAS_U8
    if (Dat_Width == 8U)
    {
        u8 *Byte_Ptr = (u8 *)Dat_Ptr;
        *Byte_Ptr = Set_Val ? (u8)(*Byte_Ptr | (u8)Mask_Val)
                           : (u8)(*Byte_Ptr & (u8)~(u8)Mask_Val);
        return Bit_Ok;
    }
#endif
    if (Dat_Width == 16U)
    {
        u16 *Half_Ptr = (u16 *)Dat_Ptr;
        *Half_Ptr = Set_Val ? (u16)(*Half_Ptr | (u16)Mask_Val)
                           : (u16)(*Half_Ptr & (u16)~(u16)Mask_Val);
        return Bit_Ok;
    }
    {
        u32 *Word_Ptr = (u32 *)Dat_Ptr;
        *Word_Ptr = Set_Val ? (u32)(*Word_Ptr | (u32)Mask_Val)
                           : (u32)(*Word_Ptr & (u32)~(u32)Mask_Val);
    }
    return Bit_Ok;
}

static inline unsigned int Pj_Bit_Get_Or_Zero(uintmax_t Dat_Val,
                                             uintmax_t Bit_Pos,
                                             size_t Dat_Width)
{
    unsigned int Bit_Val = 0U;
    (void)Pj_Bit_Get_Checked(Dat_Val, Bit_Pos, Dat_Width, &Bit_Val);
    return Bit_Val;
}

/*
 * Compatibility names requested by the user.
 * x/n are each evaluated once; sizeof(x) does not evaluate a scalar x.
 * x must meet Pj_Bit_Update_Checked's alias/RAM preconditions.
 * x and n must not modify the same scalar object without sequencing.
 * set/clr return Bit_Result; on invalid n they do not read/write x.
 * get returns 0 on invalid n; use the checked interface to distinguish errors.
 */
#define set_bit(x, n) \
    (Pj_Bit_Update_Checked(&(x), (uintmax_t)(n), sizeof(x) * CHAR_BIT, 1U))
#define clr_bit(x, n) \
    (Pj_Bit_Update_Checked(&(x), (uintmax_t)(n), sizeof(x) * CHAR_BIT, 0U))
#define get_bit(x, n) \
    (Pj_Bit_Get_Or_Zero((uintmax_t)(x), (uintmax_t)(n), sizeof(x) * CHAR_BIT))

/* Numeric halfword/octet views: independent of object byte order and union ABI. */
static inline u16 Pj_U32_Lo_U16(u32 Dat_Val)
{
    return (u16)(Dat_Val & UINT32_C(0xFFFF));
}

static inline u16 Pj_U32_Hi_U16(u32 Dat_Val)
{
    return (u16)(Dat_Val >> 16U);
}

static inline u32 Pj_U32_From_U16(u16 Hi16_Val, u16 Lo16_Val)
{
    return ((u32)Hi16_Val << 16U) | (u32)Lo16_Val;
}

#if PJ_HAS_U8
/* Byte_Pos 0 denotes the least-significant OCTET, not an object-address index. */
static inline Bit_Result Pj_U32_Byte_Get_Checked(u32 Dat_Val,
                                                uintmax_t Byte_Pos,
                                                u8 *Byte_Out)
{
    if (Byte_Out == NULL)
    {
        return Bit_Null_Output;
    }
    if (Byte_Pos >= UINTMAX_C(4))
    {
        return Bit_Index_Out_Of_Range;
    }
    *Byte_Out = (u8)((Dat_Val >> (Byte_Pos * UINTMAX_C(8))) & UINT32_C(0xFF));
    return Bit_Ok;
}
#endif

#if PJ_ENABLE_ABI_VIEWS
# include "Pj_BitLayout.h"
#endif
#endif /* PJ_MACROCFG_H */
