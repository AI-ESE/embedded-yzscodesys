# 工程资料、复盘 CSV 与门槛校验

`scripts/project_workflow.py` 使用 Python 3.10+ 标准库。它只创建资料结构、扫描文件和验证记录，不创建固件框架，不启动 IDE、编译器、下载器或调试器，也不产生授权。`check` 的 `ok=true` 表示相应阶段的**记录就绪**；不是实施已完成、硬件正确或实测通过。

## 命令

在本 Skill 目录中执行，路径按实际工程填写：

```powershell
python -B scripts/project_workflow.py init --project-root F:/Projects/MyFirmware --output F:/Projects/MyFirmware/review --name MyFirmware
python -B scripts/project_workflow.py snapshot --profile F:/Projects/MyFirmware/review/project-profile.json
python -B scripts/project_workflow.py check --profile F:/Projects/MyFirmware/review/project-profile.json --gate intake
python -B scripts/project_workflow.py check --profile F:/Projects/MyFirmware/review/project-profile.json --gate implement
python -B scripts/project_workflow.py check --profile F:/Projects/MyFirmware/review/project-profile.json --gate compile
python -B scripts/project_workflow.py check --profile F:/Projects/MyFirmware/review/project-profile.json --gate flash
python -B scripts/project_workflow.py check --profile F:/Projects/MyFirmware/review/project-profile.json --gate debug
```

工程根目录必须已存在；output 为专用目录，不能等于工程根目录。**profile 文件必须直接保存在其声明的 `output_dir` 目录内**，以保证审核页与摘要读取同一份相对图形文件。`init` 拒绝覆盖非空 output，只产生 `project-profile.json` 和三个 CSV；所有审批、复盘和构建状态均为待处理。第一次 `snapshot` 可为空，这不允许通过后续工程门槛。正常命令在 stdout 输出 JSON，成功退出 0，资料缺项、过期、非法输入或无法读取文件退出 2。`--help` 显示普通帮助文字。

`check` 返回 `gate`、`ok`、`errors`、`limitations`、`approval_digest`、`input_digest`；成功时还返回 `ready_for`。每次准备进入下一阶段时重新执行，不依赖历史输出。检查是本地只读操作。

## 摘要与路径

公开函数：

```python
approval_digest(profile: dict) -> str
input_digest(profile: dict) -> str
check_profile(profile_path, gate: str) -> dict
```

`approval_digest` 绑定方案版本、MCU、实际资料和图形文件字节、工具链及优化、工作类型/调度系统、架构、引脚和逻辑定义。**`approvals[].input_digest` 保存此方案摘要。** 它不绑定实施后的源码字节；正常实现和缺陷修复不会强迫用户重复确认同一方案。更换芯片、资料、引脚、架构、优化或方案版本会使旧确认失效。已有确认可在同一明确版本、范围下复用；方案变更只应收集受影响项的确认。本工具采用保守的统一方案摘要，修改方案时应重新登记各阶段当前版本的确认依据，并复用未受影响阶段已有的实际用户记录，不能自动伪造新确认。

`input_digest` 绑定上述方案摘要以及**即时重新扫描**的源码、头文件、启动、链接、配置和显式预编译库的路径、类别与 SHA-256。文件新增、删除和改动都会改变摘要。审批/复盘/构建结果、烧录授权和调试结果不参与摘要，避免循环。证据内容通过独立的 `*_sha256` 校验，证据编辑后旧 hash 无法通过。

资料 `documents[].path`、证据和 CSV 的相对路径以 `project_root` 为基准，统一建议使用 `/`；这些绝对引用必须位于工程根目录或专用 output 内。**图形 `diagrams[].path` 以及登记的 `waveforms[].path` 则与 HTML 审核页一致，只允许相对 profile 所在 `output_dir` 的路径**，例如文件 `review/preview.png` 在 profile 中写 `"path":"preview.png"`。图形不接受绝对路径、`..`、越出 output 的链接或缺失/空文件；不能用稳定的 missing 摘要放行。waveforms 也可不含 path，直接登记真实的内联 signals/samples，内联数据本身进入方案摘要。迁移旧记录时将曾按工程根目录写的 `review/preview.png` 调整为 `preview.png` 并重新核对方案摘要，不提供可能让显示与摘要选到不同文件的双基准回退。

所有文件引用拒绝 `..`、解析后越界和源文件符号链接。复盘 CSV 只能位于 output 内，不能将 `snapshot` 重定向到工程源文件。工程外资料应先复制到工程资料目录；不会扫描未明示的用户磁盘目录。`source_roots` 必须位于工程根目录内，不用 `exclude` 隐藏实际参与构建的文件。

默认扫描工程根目录，包括 `sdk`、`vendor`、`third_party` 和 CMSIS 的源文件。过滤 `.git`、缓存、`build`/`dist`/`out` 等生成目录、普通二进制及本工具整个 output。可配置 `work.source_roots` 和 `work.exclude`（相对于工程根目录的 glob）；范围应根据实际构建依赖人工核对。扩展名扫描无法证明 IDE 的实际构建闭包，条件编译和构建外部依赖仍需人工分析。

## Profile 结构

完整可复制空白模板在 `assets/project-profile.json`。未获资料时保留空值、空数组、false 或 pending，不填猜测值。状态通过值可用 `passed`、`verified`、`confirmed`，以及 `已通过`、`已核实`、`已确认`、`已验证`；具体字段优先选其含义对应的英文值。

UI可选分支默认`architecture.ui.enabled=false`，无UI时全部UI专项不适用。UI方案的屏幕、驱动、字库/Logo/页面资产、Flash/RAM预算、风格选择和页面映射存`architecture.ui`，随方案摘要绑定。持续追加的U1/U2/U3评分/截图/复盘结果存`review.ui_pages[]`或外部报告，每项记录当前HTML、源码/固件和界面证据摘要；不写回architecture导致无谓重确认。方案HTML/实际设计资源登记documents绑定字节，持续更新的结果报告不作为审批输入形成循环。详见[UI流程](ui-design.md)。本工具不自动计算92%或证明每页已完成三轮，执行者按真实证据逐页审核；一般compile就绪不能替代UI验收。

| 字段 | 类型、内容与要求 |
| --- | --- |
| `schema_version` | 固定 `"1.0"`，不兼容版本拒绝检查 |
| `project_name` | 非空工程名 |
| `project_root` | 已存在的工程根目录绝对路径 |
| `output_dir` | 专用资料输出目录绝对路径，可在工程内或独立目录；必须与 profile 文件所在目录一致 |
| `revision` | 当前审核方案版本，例如 `v1` |
| `mcu` | `manufacturer`、`part_number`（完整订货型号）、`package`、`family`、`vendor_region`、`sdk_ecosystem`；另 `verified` 为实际核对后设置的布尔值 |
| `documents[]` | 每项 `id/path/version/sha256/status`。必须有 `datasheet` 与 `schematic`；可增加参考手册、勘误等。path 必须是真实非空文件；每份资料版本与 hash 均核对 |
| `toolchain` | `ide/version/compiler/compiler_version/sdk/sdk_version/optimization/build_configuration`；无 SDK 时明确记录有依据的 `none`。`compatible` 布尔，`compatibility_evidence` 为所选精确型号、IDE、编译器、SDK 支持关系的分析依据 |
| `work` | `kind` 为 `new/refactor/port`；`system` 为 `bare-metal/freertos`；`original_source_path/original_system/original_analysis/original_analysis_sha256` 登记旧工程路径、真实调度、实际读取分析文件及其 hash；重构/移植必填，不能只写“已分析”。`source_roots` 为非空目录列表，默认 `["."]`；`exclude` 为 glob 数组；`precompiled_libraries` 见下文 |
| `architecture` | `summary`、`modules[]`、`tasks[]`、`interrupts[]`、`data_flows[]`；无中断应显式 `[]`。模块/任务对象可添加层级、职责、周期、优先级、栈、依赖、所有权和初始化等工程信息 |
| `pins[]` | 每个封装物理脚一项；下表列出字段。电源、地、保留、NC、未用脚同样登记，以有理由的 `N/A: ...` 说明软件不适用字段 |
| `logic[]` | 每项 `id/description/requirements/source/code/pin_ids`。pin_ids 数组只可引用现有引脚；无直接关联脚可为空，需在 description/requirements 说明 |
| `diagrams[]` | 每项 `id/title/kind/path/source/caption`。kind 明确设计预期、仿真或实测；path 相对 profile/output 目录，必须为真实非空文件，图形字节纳入方案摘要 |
| `waveforms[]` | 初始可为 `[]`；每项可沿用图形字段，并加入单位、边沿、极性、约束、模型、输入、仪器和采集条件。登记 path 时按 profile/output 目录读取真实非空文件；仅内联 signals/samples 时可不设 path。不得无数据声称实测 |
| `approvals[]` | 必须各有 A1–A5 一项：`stage/status/revision/input_digest/user_evidence/user_evidence_sha256`。input_digest 是 `approval_digest(profile)`；user_evidence 是保存实际用户回复及所指版本/范围的证据文件。模板、HTML 勾选、工具生成的自述不等于用户确认 |
| `review` | `inventory_path/logic_pins_path/rule_coverage_path` 为下述 CSV 的路径，必须位于 output 内 |
| `build` | `status/exit_code/error_count/configuration/optimization/input_digest/log/log_sha256/artifact/artifact_sha256/warnings_reviewed/optimizer_reviewed/production`。实际生产配置构建后才能填写通过、整数退出码0和错误数0；input_digest 必须对应当前输入；warnings_reviewed、optimizer_reviewed、production 为布尔 |
| `hardware` | 见下文。任何模板初值不能替代当前接线、目标识别或实际授权 |

每个 `pins[]` 包含：

| 字段 | 含义 |
| --- | --- |
| `id` | 稳定且唯一的引脚 ID |
| `physical_pin` | 当前具体封装物理脚号 |
| `gpio` | GPIO、复用或固定管脚标识 |
| `function` | 当前用途及资源 |
| `net` | 原理图网络和外围电路位置 |
| `direction` | 输入、输出、双向、电源等实际方向 |
| `active_level` | 有效电平及依据 |
| `inversion` | 外围驱动、隔离和反相链，无反相明确 `none` |
| `pull` | 上下拉/输出类型与实际配置 |
| `reset_state` | 上电/复位状态 |
| `run_state` | 正常运行状态与动作 |
| `fault_state` | 故障/超时安全状态 |
| `source` | 规格书、原理图版本与页码/位号等位置 |
| `code` | 实现前拟采用接口，实施后实际 HDL/业务代码位置 |
| `review_status` | 待确认/已确认等登记；实际用户确认仍由 A3/A4 证据证明 |

`hardware` 包含 `target_identified`、`connection_confirmed_by_user`（布尔）、`probe`、`target_part`、`target_board`、`flash_regions`、`flash_authorization`、`flash_result`、`verify_result`、`debug_connection`、`debug_log`、`debug_log_sha256`。

`flash_regions` 为非空 `[{"start":"0x08000000","length":"0x10000"}]`，地址非负、长度正数，使用具体工程已确认范围，不默认整片擦除。`flash_authorization` 是对象，包含 `status/input_digest/artifact_sha256/target_part/target_board/probe/flash_regions/user_evidence/user_evidence_sha256`；它绑定当前输入、真实产物、目标板/芯片、探针和明确范围。实际已有授权和接线记录直接复用，不重复向用户索取同一许可；本工具不制造授权。

`debug_connection` 是对象，包含 `channel/port/target_part/target_board`，并按通道填写波特率、SWO 配置、探针和调试配置等：例如 `{"channel":"UART","port":"COM3","baud":115200,"target_part":"实际型号","target_board":"实际板卡"}`。SWD/JTAG 并不自动提供 printf；channel 写真实观测方式，例如 UART、SWO、RTT、JTAG 或厂商接口，并记录配置。仅写 true 或“已连接”不能通过。debug gate 是采集前就绪检查；`flash_result/verify_result` 可保留 pending，`debug_log` 空值表明尚无采集证据，不能宣称现场调试完成。填写调试日志时必须同时填写匹配的 hash。

## 三个 CSV

UTF-8、逗号分隔、首行列名；使用 `csv` 工具编辑或确保单元格内逗号和换行正确引用。每轮独立记录，状态默认 pending。`snapshot` 按稳定 ID/文件路径保留未变化输入且 hash 仍匹配的证据；修改文件/方案或编辑证据会使受影响项退回 pending。全局规则覆盖和逻辑/引脚交叉分析保守绑定当前全部输入，源码新增或变化后需重核相关影响。扫描不会自动填写通过结果。

### review-files.csv

每个源/头/启动/链接/配置文件一行，包括实际参与构建的 SDK 和第三方。基础列为：

| 列 | 内容 |
| --- | --- |
| `path` | 相对工程根目录的文件路径（唯一） |
| `category` | source/header/startup/linker/configuration；SDK 对应 sdk-source/sdk-header/sdk-configuration；显式库为 precompiled-library |
| `sha256` | 当前文件字节摘要 |
| `context_digest` | 当前方案摘要；方案变化后须重核文件适用上下文 |
| `applicable_rules` | 每个文件必填，列出适用规则编号、适用范围或引用具体规则分析文件 |
| `not_applicable_reason` | SDK 自有命名例外、不可得内部源码等具体理由；不表示整个 SDK 已免检 |
| `source_available` | 普通文本源为 yes，显式预编译库为 no |
| `abi_interfaces` | 预编译库 ABI、公开接口、存储模型和集成依据 |
| `unresolved` | 未关闭阻断项；通过门槛时必须为空 |

每一轮 C1/C2/C3 均有以下五列，共15列：`C1_status/C1_evidence/C1_evidence_sha256/C1_input_digest/C1_notes`，C2、C3 使用相同后缀。status 为该轮结果，evidence 为真实报告路径，evidence_sha256 为其真实内容摘要，input_digest **填写本行 sha256**；notes 写方法、发现、修复和位置。三轮的证据内容 SHA-256 必须互不相同，改名或复制同一日志无效。C1 查形式与基础规则，C2 查语义与接口，C3 查组合与遗漏；报告可覆盖多文件，但必须具体列明文件及分析依据。

显式预编译库在 `work.precompiled_libraries` 登记，例如 `[{"path":"lib/vendor.lib","abi_interfaces":"真实 ABI、编译器兼容与公开头文件位置"}]`。普通二进制不自动扫描；显式库记录二进制摘要，三轮只复盘适用性、ABI、公开接口和集成，`source_available=no`、`not_applicable_reason` 明确**内部源码不可得/未验证**。仅预编译库、没有实际源/头/启动/链接/配置范围时，compile 不能以空范围通过。

### review-logic-pins.csv

每项逻辑以及每个引脚分别一行，不能按某轮只看代码、另一轮只看引脚凑次数。基础列：

| 列 | 内容 |
| --- | --- |
| `kind` | logic 或 pin |
| `id` | profile 中对应的稳定唯一 ID；与 kind 共同唯一 |
| `source` | 对应资料位置 |
| `code` | 对应代码/拟定接口位置 |
| `item_digest` | 当前条目定义及全工程输入摘要，由 snapshot 产生 |
| `verification_level` | 默认 software-analysis；另可记录 simulation 或 measured，但必须有真实模型/数据/采集条件 |
| `unresolved` | 未关闭阻断项；通过时必须为空 |

L1/L2/L3 每轮五列：`L1_status/L1_evidence/L1_evidence_sha256/L1_input_digest/L1_notes`，L2、L3 使用相同后缀。input_digest **填写本行 item_digest**。证据文件和 hash 必须存在且三轮内容互不相同。L1 正向追踪，L2 反向追踪，L3 全局场景/边界/实时与优化相关复核。每项都须三轮齐全。

### rule-coverage.csv

与 `assets/rule-catalog.json` 中每条规则一一对应；不允许漏行、添加替代行、复用旧规则定义。所有列：

| 列 | 内容 |
| --- | --- |
| `id/document/description/mode` | catalog 的规则编号、来源、描述和覆盖方式 |
| `rule_digest` | 当前完整 catalog 条目与其 document 所指规范正文真实 SHA-256 的组合摘要，由 snapshot 产生；规范正文路径相对 Skill 根目录，缺失、空文件或越界拒绝检查 |
| `status` | passed/verified 等通过状态，或有具体理由的 not_applicable |
| `evidence/evidence_sha256` | 真实自动检查或人工分析文件及实际内容摘要 |
| `input_digest` | 当前 `input_digest(profile)`，不是方案摘要 |
| `notes` | 具体代码位置、检查方法、例外和限制；不适用时理由必填 |
| `unresolved` | 未关闭阻断项；通过时必须为空 |

catalog 缺失或为空时 `snapshot` 可生成空表但明确警告，compile 及后续门槛一定拒绝。即使 catalog 的规则标题未改，只要实际规范正文变化，引用该正文的旧覆盖证据就会失效，snapshot 将对应条目退回 pending，未变规范的证据可以保留。规范升级本身不改变用户方案确认摘要或工程 input_digest；重新复盘规则后再检查门槛。自动检查器的零发现不能替代人工语义分析、规格书核对和需要硬件的实测。

## 工程 Log 的基础检查

进入 `compile` 及后续门槛时，工程根目录必须有普通目录 `Log`，其中两份 UTF-8 文件必须存在且非空，并至少包含以下字段的非空记录值：

- `Log/版本记录.md`：`版本号`、`修改日期`、`修改涉及文件`、`修改内容或者功能`。
- `Log/提示词记录.md`：`提示词时间`、`精简提示词内容`、`最终改善输出`。

字段按模板使用独立行 `字段：值` 或 `字段: 值`，值可写在后续行，例如修改涉及文件的列表；可使用普通 Markdown 列表或字段名加粗。仅有标题、空文件、只有空字段标签均不能通过。`intake` 和 `implement` 阶段尚未搭建工程，不强制创建这两份实施记录。

这是存在性、基础字段和非空值检查，不证明每次问答和修改均已记录，也不证明记录真实、每条完整、日期正确、文件范围齐全或历史从未覆盖。新增记录必须依 LG01–LG06 在末尾追加、条目间空行分隔；`project_log.py` 可辅助追加。Log 文字本身不触发方案重新确认；不能用它代替源码、三轮复盘、用户确认或真实工具证据。

## 逐级检查边界

| gate | 在前级条件基础上检查 |
| --- | --- |
| intake | 真实完整 MCU、已核实规格书/原理图文件与版本/hash、匹配 IDE/编译器/SDK 和优化配置、工作类型、裸机或 FreeRTOS；重构/移植还有旧工程分析 |
| implement | 架构、全部引脚与逻辑资料；A1–A5 对应当前方案版本和方案摘要，均有真实用户证据文件/hash |
| compile | 两份工程 Log 存在且非空、基本字段有值；当前非空完整文件范围、每文件 C1/C2/C3；每项逻辑和引脚 L1/L2/L3；全部规则覆盖；证据存在、hash匹配、每组三轮内容不同、没有未关闭阻断项 |
| flash | 当前输入的生产配置实际构建0错误、退出码0、匹配配置与优化、日志/固件真实hash、告警及优化已分析；当前芯片/板卡/探针、用户确认接线、绑定产物与具体擦写范围的授权证据 |
| debug | 具体可用观测通道、端口/参数及当前目标；若已记录观察日志则检查其文件/hash |

任意工具都不能从 hash、人工填入状态或测试夹具本身判断用户证据是否真实、是否覆盖完整语义；应保存原始用户记录、可复查分析和真正工具输出。本工具拒绝已知的空项、过期摘要、漏项、重复三轮证据与越界路径，但不宣称自动证明规则语义、全部物理管脚、电气连接或实机时序。
