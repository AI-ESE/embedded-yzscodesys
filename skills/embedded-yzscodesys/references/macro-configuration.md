# 公共基础类型、位操作与可选内存视图

本模板用于新建或适配工程的公共基础配置。初次确认 MCU、编译器、语言标准、SDK 类型定义和 ABI 后，将 `assets/headers/Pj_MacroCfg.h` 放入 **`Common/Inc/Pj_MacroCfg.h`**；需要调试内存视图时，同目录加入 `Pj_BitLayout.h`。不要放在产品参数文件，也不要直接覆盖 SDK 或厂商的 typedef。

头文件不放设备电压、阈值、运行周期、产品功能开关或校准数值。产品参数继续归产品配置；器件寄存器定义继续归厂商 SDK / HDL。`PJ_` 开关只控制本基础类型模板的能力和可选 ABI 视图。

## 默认六种类型与兼容别名

用户指定以下六种为**新代码与基础整型参数的默认首选**，不是要求把变量起名为 `u32`。精确宽度由 `<stdint.h>` 提供，并核对 `sizeof(type) * CHAR_BIT`：

```c
typedef uint32_t u32;
typedef uint16_t u16;
typedef uint8_t  u8;   /* 仅在真实 8 位类型存在时提供 */
typedef int32_t  s32;
typedef int16_t  s16;
typedef int8_t   s8;   /* signed 8 位，不能写成 u8 或不存在的 S8 */

void FML_Chg_Set(u16 Tag_Vol, const u8 *Dat_Buf, u16 Dat_Len);
```

变量、参数、结构体/联合体类型和成员仍使用 `Pascal_Underscore`。用户允许 `Charge → Chg`、`Target → Tag`，`Voltage → Vol`、`Buffer → Buf`、`Data → Dat`；不由此改写 SDK、第三方接口或外部数据字段。

| 首选别名 | 标准精确类型 | 仅为兼容而保留的用户别名 |
| --- | --- | --- |
| `u32` | `uint32_t` | `Uint32`、`INT32U` |
| `u16` | `uint16_t` | `Uint16`、`INT16U` |
| `u8` | `uint8_t`，条件提供 | `Uint8`、`INT8U`，同条件提供 |
| `s32` | `int32_t` | 无新增兼容名 |
| `s16` | `int16_t` | `INT16S` |
| `s8` | `int8_t`，条件提供 | 无新增大写 `S8` 类型 |

这些显式用户别名、`clr_bit / set_bit / get_bit` 是命名兼容例外，不把它们推广成新结构体或成员的命名方式。`uintmax_t` 和 `size_t` 在底层 helper 中保留其标准含义：前者接收不应先被窄化的位号/掩码，后者表达 `sizeof` 宽度；业务接口优先使用上述六种默认别名。

默认 `PJ_ENABLE_COMPAT_ALIASES=1`。SDK 已拥有 `Uint16` 等名称时，在第一次包含头文件前设置 `PJ_ENABLE_COMPAT_ALIASES=0`，或完成单一所有者的适配。预处理器不能可靠判断一个 typedef 是否已存在，不能用 `#ifndef Uint16` 检查类型。若 SDK 也拥有 `u32` 等默认名称，应核对实际类型并选择一处统一声明，不能盲目叠加此模板。

## 无真实 8 位类型的平台

`PJ_HAS_U8` 是派生能力值，不由工程手动伪造。只有 `CHAR_BIT == 8`、`UINT8_MAX` 与 `INT8_MAX` 均存在，且未设置 `PJ_DISABLE_U8=1` 时，它才为 1；此时才提供全部 8 位别名、8 位调试视图和 octet helper。否则它为 0，`u8 / s8 / Uint8 / INT8U / View_U8` 均不提供。

需要强制真实 8 位接口的工程可设置 `PJ_REQUIRE_U8=1`，缺少时编译明确失败。需要关闭模板的 8 位接口进行适配或测试时用 `PJ_DISABLE_U8=1`，不改写标准头，不拿 `u16` 冒充 `u8`。

C28x 的一个 C byte 为 16 位，`sizeof(char) == 1` 仍然成立，因此不能把 `sizeof(type)` 直接当作 octet 数。厂商资料指出对应编译器没有真正的 `uint8_t / int8_t`，一些 SDK 将同名类型映射成 16 位；此模板仍通过 `CHAR_BIT` 禁用自己的 8 位别名。8 位通信数据应使用经过审核的 16 位容器、明确的低 8 位掩码及目标支持的字节访问方法，不能改称真实 8 位类型。[TI C28x byte 说明](https://software-dl.ti.com/ccs/esd/documents/c2000_byte-accesses-with-the-c28x-cpu.html)、[TI 数据类型说明](https://downloads.ti.com/docs/esd/SPRU514/data-types-stdz0555922.html)。

## 位操作契约

默认使用无符号整数和掩码，不依赖位域顺序、union 布局或端序。位号从数值的最低有效位 0 开始；掩码以 `UINTMAX_C(1)` 构造并先检查边界，避免有符号 `1 << 31` 的问题。

| 接口 | 成功与失败 |
| --- | --- |
| `set_bit(x, n)` | 设置位，返回 `Bit_Result`；非法位号不读取/写入目标值 |
| `clr_bit(x, n)` | 清除位，返回 `Bit_Result`；非法位号不读取/写入目标值 |
| `get_bit(x, n)` | 返回 0 或 1；非法位号也返回 0，不能据此区别“位清零”与“位号错误” |
| `Pj_Bit_Mask_Checked(Bit_Pos, Dat_Width, &Mask_Val)` | `Bit_Ok` 时输出掩码；失败保留原输出 |
| `Pj_Bit_Get_Checked(Dat_Val, Bit_Pos, Dat_Width, &Bit_Val)` | `Bit_Ok` 时输出 0/1；失败保留原输出 |
| `Pj_Bit_Update_Checked(Dat_Ptr, Bit_Pos, Dat_Width, Set_Val)` | 在指定宽度的默认别名对象上更新；非零 `Set_Val` 为置位，0 为清位 |

错误码为 `Bit_Null_Output`、`Bit_Index_Out_Of_Range`、`Bit_Width_Invalid`。`Bit_Ok == 0`；不要把 `if (set_bit(...))` 当作旧宏的值表达式，它现在表示“出现错误”。兼容名称保留，表达式返回值契约已明确为状态。

通用 checked 掩码/读取 helper 的逻辑宽度范围为 1..32 位，位号必须小于该宽度；更新对象限于真实的 8/16/32 位别名。更宽整数不在此模板的兼容宏契约内。

`x`、`n` 每次调用各只求值一次。`sizeof(x)` 对这里要求的标量对象不求值；宏作为单个表达式可用于 `if / else`。即使位号非法，`&(x)` 中的索引或指针计算仍会求值一次；`get_bit` 也仍读取一次传入值。`n` 必须是整数表达式，负整数转换后被判为越界。`x` 与 `n` 不能同时无序修改同一个标量，例如不要写 `set_bit(Dat_Buf[Dat_Pos++], Dat_Pos++)`。

**置/清位前置条件**：`x` 必须是实际的 `u8 / u16 / u32`（或其完全相同的兼容别名）非 volatile RAM 左值，不能只是另一个恰好同大小的基础类型，不能是 signed、布尔、位域或寄存器。C99 路径按实际精确类型宽度分派 typed helper；它不能靠大小识别任意其他类型，违背此前置条件可能违反别名规则。调用 `Pj_Bit_Update_Checked` 时，指针、真实类型和 `Dat_Width = sizeof(对象) * CHAR_BIT` 也必须一致；支持实际存在的 8、16、32 位对象。

这些操作不提供原子性、临界区、总线访问保证或寄存器副作用处理。普通 read-modify-write 不适用于 W1C/W1S、读清除寄存器、需要专用 SET/CLR 地址的外设，也不能代替 ISR/任务共享数据同步。寄存器操作按芯片规格书和厂商访问器由 HDL 实现。

```c
u32 Tag_Word = UINT32_C(0);
Bit_Result Check_Val = set_bit(Tag_Word, 31U);
if (Check_Val != Bit_Ok)
{
    /* 按本模块错误策略处理，不把非法位号当成功。 */
}
```

## 数值拆分与数据编码

`Pj_U32_Lo_U16`、`Pj_U32_Hi_U16`、`Pj_U32_From_U16(Hi16_Val, Lo16_Val)` 提供数值高/低 16 位视图，不依赖内存次序。

真实 8 位类型存在时，`Pj_U32_Byte_Get_Checked` 的 `Byte_Pos = 0..3` 按最低到最高有效 **octet** 取值，0 永远表示最低 8 位。它不表示“对象的第一个地址字节”。非法位置保留输出并返回错误。

通信、文件、Flash 参数和持久化格式按协议明确 LE/BE、字段宽度及 signed 编码。按掩码/移位把 octet 写入明确顺序的输出缓冲区；无 8 位对象的平台另行适配 octet 容器和外设接口。不要把 union 的 `Byte_Dat`、结构体内存或 `sizeof(struct)` 直接当作跨平台线格式。

## 可选 ABI 位域和联合体调试视图

默认 `PJ_ENABLE_ABI_VIEWS=0`，即使包含 `Pj_BitLayout.h` 也不声明非移植视图。确需调试视图时，在第一次包含头文件前显式配置：

```c
/* 仅示例配置形式；取值必须来自当前目标 ABI 文档和实际探针结果。 */
#define PJ_ENABLE_ABI_VIEWS 1
#define PJ_ABI_BYTE_ORDER 1234
#define PJ_ABI_BITFIELD_ORDER 1234
#include "Pj_MacroCfg.h"
```

`PJ_ABI_BYTE_ORDER`：1234 表示低有效 octet / halfword 位于低地址，4321 表示相反顺序。`PJ_ABI_BITFIELD_ORDER`：1234 表示先声明字段从分配单元最低位开始，4321 表示从最高位开始。二者是独立 ABI 选择，不能由 CPU 名称、端序或主机结果推断另一项。

`u8 / u16 / u32` 位域底层类型在 C 中依赖实现支持，所有 C 标准版本和编译器并非都支持这些类型的位域；支持后也必须检查分配单元、对齐和跨单元行为。GCC 明确将位域分配顺序和跨单元行为交给 ABI 决定。[GCC 位域实现说明](https://gcc.gnu.org/onlinedocs/gcc/Structures-unions-enumerations-and-bit-fields-implementation.html)。

| 类型 | 提供的成员 / 视图 |
| --- | --- |
| `Bit_U8 / Bit_U16 / Bit_U32` | `Bit_0` 到实际最高位；真实位号允许数字段 |
| `View_U8` | `U8_Val`、signed 的 `S8_Val`、`Bits_Dat`、`Bytes_Dat`、`Byte_Dat[1]` |
| `View_U16` | `U16_Val`、`S16_Val`、`Bits_Dat`，有 u8 时加 `Bytes_Dat`、`Byte_Dat[2]` |
| `View_U32` | `U32_Val`、`S32_Val`、`Bits_Dat`、`Half_Dat`，有 u8 时加 `Bytes_Dat`、`Byte_Dat[4]` |
| `Half_U32` | `Lo16_Val / Hi16_Val`，字段声明顺序由明确的 byte-order 配置决定 |
| `Byte_U8 / Byte_U16 / Byte_U32` | `Byte_0` 表示最低有效 octet；`Byte_Dat[]` 数组下标则始终是实际存储地址顺序 |

头文件对每个位域、字节、halfword 结构与 union 做 `sizeof * CHAR_BIT` 编译期核对。**大小相等不证明位序正确**；目标构建还需运行逐位 walking-one、各字节不同的数值、signed 与高低半字探针，并保存编译器、ABI、优化和结果。错误的 ABI 配置也可能通过大小检查。

这些是 ABI 专用的调试内存视图，不是可移植的 reinterpret API。**C++ 只读取当前活动的 union 成员**，不要写 `U32_Val` 后读 `Bits_Dat` 或 `S32_Val` 并宣称符合可移植 C++。C 中的跨成员访问也应按编译器/ABI规则和目标证据处理；不要把主机 C 的调试探针改写成跨平台库契约。

| 原有名称 / 写法 | 模板名称 / 处理 |
| --- | --- |
| `_8_bits / _16_bits / _32_bits` | `Bit_U8 / Bit_U16 / Bit_U32`；不生成保留标识符公共类型 |
| `_8_type / _16_type / _32_type` | `View_U8 / View_U16 / View_U32` |
| `SBit32` | `Half_U32`，以Lo16_Val/Hi16_Val表达低/高16位 |
| `UDWords` | `View_U32`，提供unsigned、signed及Half_Dat视图；C++不跨活动成员读取 |
| 字段 `U8 / S8 / bits` | `U8_Val / S8_Val / Bits_Dat`；`S8_Val` 的类型为 `s8` |
| 直接将 `unsigned int` 当 32 位 | `uint32_t → u32 → INT32U`，带实际位宽核对 |
| `1 << 31` | checked 无符号掩码；默认整数路径不需要 union |

## 语言与验证边界

正式模板要求 C99+ 或 C++11+，具有可用 `<stdint.h>`、`uintmax_t`、精确 16/32 位类型与 `inline`。C90 工程需要经过工程审核的精确类型适配、编译期核对与函数链接策略，不能把此模板直接复制后宣称兼容；当前文件对 C90 / C++98 明确拒绝编译。无真实 16/32 位精确类型时同样明确失败。

```powershell
python -B -m unittest discover -s tests -p test_macro_config.py -v
```

主机验证使用 MinGW GCC/G++ 13.2.0，`-std=c99 / c++11 -O2 -Wall -Wextra -Wconversion -Wsign-conversion -Werror -pedantic-errors`。它们实际编译并运行别名位宽、signed S8、位31、参数副作用、`if/else`、非法位号、checked 输出保留、数值高低16位和 octet 提取；同时检查默认无非移植视图、明确 opt-in 的主机 C 视图和 C++ 活动成员访问、禁用 u8 和缺能力报错。

上述绝对路径仅记录本次主机验证环境，**不是公共头运行时依赖**。测试优先读取 `CC / CXX` 中的本机编译器可执行文件路径，再查 `PATH` 中的 `gcc / g++`，本机 Strawberry 路径只是最后回退。未找到 C/C++ 编译器会明确报告 skipped（编译验证未执行），不得把跳过当成编译通过；`CC / CXX` 不接受拼接的 shell 命令或附加参数。公共头本身不依赖 Python、这些路径或主机工具。

`PJ_DISABLE_U8=1` 仅模拟模板无 8 位接口的分支，**不是执行过 C28x 交叉编译**。主机 little-endian / LSB-first 观测只证明该次主机 ABI；CCS/C28x、Keil、ESP 或其他目标仍需对应目标工具链构建和适用的硬件/ABI探针证据。
