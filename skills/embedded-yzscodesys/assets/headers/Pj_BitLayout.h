/*
 * Optional ABI-specific bit-field / union DEBUG views.
 * Destination: Common/Inc/Pj_BitLayout.h (next to Pj_MacroCfg.h).
 * These definitions are not a portable representation conversion API.
 * C++: read only the active union member; no cross-member type punning here.
 */
#ifndef PJ_BITLAYOUT_H
#define PJ_BITLAYOUT_H
#include "Pj_MacroCfg.h"

#if PJ_ENABLE_ABI_VIEWS
# if !defined(PJ_ABI_BYTE_ORDER)
#  error "Set PJ_ABI_BYTE_ORDER to the reviewed target ABI: 1234 (LSB byte first) or 4321."
# elif (PJ_ABI_BYTE_ORDER != 1234) && (PJ_ABI_BYTE_ORDER != 4321)
#  error "PJ_ABI_BYTE_ORDER must be 1234 or 4321."
# endif
# if !defined(PJ_ABI_BITFIELD_ORDER)
#  error "Set PJ_ABI_BITFIELD_ORDER to the observed allocation: 1234 (LSB field first) or 4321."
# elif (PJ_ABI_BITFIELD_ORDER != 1234) && (PJ_ABI_BITFIELD_ORDER != 4321)
#  error "PJ_ABI_BITFIELD_ORDER must be 1234 or 4321."
# endif

/* uint8_t/uint16_t/uint32_t bit-fields rely on implementation support in C. */
#if PJ_HAS_U8
typedef struct Bit_U8
{
#if PJ_ABI_BITFIELD_ORDER == 1234
    u8 Bit_0 : 1;
    u8 Bit_1 : 1;
    u8 Bit_2 : 1;
    u8 Bit_3 : 1;
    u8 Bit_4 : 1;
    u8 Bit_5 : 1;
    u8 Bit_6 : 1;
    u8 Bit_7 : 1;
#else
    u8 Bit_7 : 1;
    u8 Bit_6 : 1;
    u8 Bit_5 : 1;
    u8 Bit_4 : 1;
    u8 Bit_3 : 1;
    u8 Bit_2 : 1;
    u8 Bit_1 : 1;
    u8 Bit_0 : 1;
#endif
} Bit_U8;

typedef struct Byte_U8
{
#if PJ_ABI_BYTE_ORDER == 1234
    u8 Byte_0;
#else
    u8 Byte_0;
#endif
} Byte_U8;

#endif
typedef struct Bit_U16
{
#if PJ_ABI_BITFIELD_ORDER == 1234
    u16 Bit_0 : 1;
    u16 Bit_1 : 1;
    u16 Bit_2 : 1;
    u16 Bit_3 : 1;
    u16 Bit_4 : 1;
    u16 Bit_5 : 1;
    u16 Bit_6 : 1;
    u16 Bit_7 : 1;
    u16 Bit_8 : 1;
    u16 Bit_9 : 1;
    u16 Bit_10 : 1;
    u16 Bit_11 : 1;
    u16 Bit_12 : 1;
    u16 Bit_13 : 1;
    u16 Bit_14 : 1;
    u16 Bit_15 : 1;
#else
    u16 Bit_15 : 1;
    u16 Bit_14 : 1;
    u16 Bit_13 : 1;
    u16 Bit_12 : 1;
    u16 Bit_11 : 1;
    u16 Bit_10 : 1;
    u16 Bit_9 : 1;
    u16 Bit_8 : 1;
    u16 Bit_7 : 1;
    u16 Bit_6 : 1;
    u16 Bit_5 : 1;
    u16 Bit_4 : 1;
    u16 Bit_3 : 1;
    u16 Bit_2 : 1;
    u16 Bit_1 : 1;
    u16 Bit_0 : 1;
#endif
} Bit_U16;

typedef struct Bit_U32
{
#if PJ_ABI_BITFIELD_ORDER == 1234
    u32 Bit_0 : 1;
    u32 Bit_1 : 1;
    u32 Bit_2 : 1;
    u32 Bit_3 : 1;
    u32 Bit_4 : 1;
    u32 Bit_5 : 1;
    u32 Bit_6 : 1;
    u32 Bit_7 : 1;
    u32 Bit_8 : 1;
    u32 Bit_9 : 1;
    u32 Bit_10 : 1;
    u32 Bit_11 : 1;
    u32 Bit_12 : 1;
    u32 Bit_13 : 1;
    u32 Bit_14 : 1;
    u32 Bit_15 : 1;
    u32 Bit_16 : 1;
    u32 Bit_17 : 1;
    u32 Bit_18 : 1;
    u32 Bit_19 : 1;
    u32 Bit_20 : 1;
    u32 Bit_21 : 1;
    u32 Bit_22 : 1;
    u32 Bit_23 : 1;
    u32 Bit_24 : 1;
    u32 Bit_25 : 1;
    u32 Bit_26 : 1;
    u32 Bit_27 : 1;
    u32 Bit_28 : 1;
    u32 Bit_29 : 1;
    u32 Bit_30 : 1;
    u32 Bit_31 : 1;
#else
    u32 Bit_31 : 1;
    u32 Bit_30 : 1;
    u32 Bit_29 : 1;
    u32 Bit_28 : 1;
    u32 Bit_27 : 1;
    u32 Bit_26 : 1;
    u32 Bit_25 : 1;
    u32 Bit_24 : 1;
    u32 Bit_23 : 1;
    u32 Bit_22 : 1;
    u32 Bit_21 : 1;
    u32 Bit_20 : 1;
    u32 Bit_19 : 1;
    u32 Bit_18 : 1;
    u32 Bit_17 : 1;
    u32 Bit_16 : 1;
    u32 Bit_15 : 1;
    u32 Bit_14 : 1;
    u32 Bit_13 : 1;
    u32 Bit_12 : 1;
    u32 Bit_11 : 1;
    u32 Bit_10 : 1;
    u32 Bit_9 : 1;
    u32 Bit_8 : 1;
    u32 Bit_7 : 1;
    u32 Bit_6 : 1;
    u32 Bit_5 : 1;
    u32 Bit_4 : 1;
    u32 Bit_3 : 1;
    u32 Bit_2 : 1;
    u32 Bit_1 : 1;
    u32 Bit_0 : 1;
#endif
} Bit_U32;

#if PJ_HAS_U8
typedef struct Byte_U16
{
#if PJ_ABI_BYTE_ORDER == 1234
    u8 Byte_0;
    u8 Byte_1;
#else
    u8 Byte_1;
    u8 Byte_0;
#endif
} Byte_U16;

typedef struct Byte_U32
{
#if PJ_ABI_BYTE_ORDER == 1234
    u8 Byte_0;
    u8 Byte_1;
    u8 Byte_2;
    u8 Byte_3;
#else
    u8 Byte_3;
    u8 Byte_2;
    u8 Byte_1;
    u8 Byte_0;
#endif
} Byte_U32;

#endif

typedef struct Half_U32
{
#if PJ_ABI_BYTE_ORDER == 1234
    u16 Lo16_Val;
    u16 Hi16_Val;
#else
    u16 Hi16_Val;
    u16 Lo16_Val;
#endif
} Half_U32;

#if PJ_HAS_U8
typedef union View_U8
{
    u8 U8_Val;
    s8 S8_Val;
    Bit_U8 Bits_Dat;
    Byte_U8 Bytes_Dat;
    u8 Byte_Dat[1];
} View_U8;
#endif

typedef union View_U16
{
    u16 U16_Val;
    s16 S16_Val;
    Bit_U16 Bits_Dat;
#if PJ_HAS_U8
    Byte_U16 Bytes_Dat;
    u8 Byte_Dat[2];
#endif
} View_U16;

typedef union View_U32
{
    u32 U32_Val;
    s32 S32_Val;
    Bit_U32 Bits_Dat;
    Half_U32 Half_Dat;
#if PJ_HAS_U8
    Byte_U32 Bytes_Dat;
    u8 Byte_Dat[4];
#endif
} View_U32;

/* Size checks detect padding/packing mismatches; they DO NOT prove bit order. */
typedef char Pj_Bit_U16_Size_Check[(sizeof(Bit_U16) * CHAR_BIT == 16U) ? 1 : -1];
typedef char Pj_Bit_U32_Size_Check[(sizeof(Bit_U32) * CHAR_BIT == 32U) ? 1 : -1];
typedef char Pj_View_U16_Size_Check[(sizeof(View_U16) * CHAR_BIT == 16U) ? 1 : -1];
typedef char Pj_View_U32_Size_Check[(sizeof(View_U32) * CHAR_BIT == 32U) ? 1 : -1];
typedef char Pj_Half_U32_Size_Check[(sizeof(Half_U32) * CHAR_BIT == 32U) ? 1 : -1];
#if PJ_HAS_U8
typedef char Pj_Bit_U8_Size_Check[(sizeof(Bit_U8) * CHAR_BIT == 8U) ? 1 : -1];
typedef char Pj_View_U8_Size_Check[(sizeof(View_U8) * CHAR_BIT == 8U) ? 1 : -1];
typedef char Pj_Byte_U8_Size_Check[(sizeof(Byte_U8) * CHAR_BIT == 8U) ? 1 : -1];
typedef char Pj_Byte_U16_Size_Check[(sizeof(Byte_U16) * CHAR_BIT == 16U) ? 1 : -1];
typedef char Pj_Byte_U32_Size_Check[(sizeof(Byte_U32) * CHAR_BIT == 32U) ? 1 : -1];
#endif
#endif /* PJ_ENABLE_ABI_VIEWS */
#endif /* PJ_BITLAYOUT_H */
