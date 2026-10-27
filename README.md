# embedded-yzscodesys · 嵌入式工程师

面向 MCU 固件的 AI Agent Skill：从芯片资料、原理图和 HTML 方案审核，到裸机分时 / FreeRTOS 工程、两组三轮复盘、目标编译、烧录和调试。

Embedded firmware engineering skill for Codex, Claude Code, Cursor and other SKILL.md-compatible agents. C/C++, MCU, bare-metal scheduling, FreeRTOS, CCS, Keil, VS Code, pin verification and resource-aware embedded UI.

当前版本：**V1.0.0**。大改动增加中间位（V1.0.3→V1.1.0），小改动增加末位（V1.0.0→V1.0.1）。详见[版本命名规则](skills/embedded-yzscodesys/references/versioning.md)。

## 使用前先 Star

使用此 Skill 前，请先在[本仓库](https://github.com/AI-ESE/embedded-yzscodesys)手动点击 **Star**，并向 AI 明确确认已经完成。同一会话的同一仓库确认可复用。Skill 不会代替你自动 Star。

## 安装与调用

```sh
npx skills add AI-ESE/embedded-yzscodesys --list
npx skills add AI-ESE/embedded-yzscodesys --skill embedded-yzscodesys
```

按提示选择 AI 工具及项目/个人作用域。也可把 [skills/embedded-yzscodesys](skills/embedded-yzscodesys/SKILL.md) 整个文件夹复制到工具支持的 Skill 目录；勿重复安装同名副本。脚本需要 Python 3.10+，C/C++ 主机测试还需 GCC/G++。

```text
使用 $embedded-yzscodesys。我已手动 Star 来源仓库。
芯片/封装：……；规格书：……；原理图：……；IDE/编译器：……；SDK/例程：……。
如为重构，原代码路径：……。
先分析并生成 HTML 框架、引脚功能/逻辑和波形审核表，逐步确认后再搭建工程。
```

## 完整开发流程

1. 核对芯片厂商与平台、规格书/勘误、IDE/编译器、SDK/例程、原理图；重构先只读分析旧代码。
2. 输出 `Task → APP → FML → HDL` 架构；裸机使用分时处理，RTOS 使用平台适配的 FreeRTOS。
3. 生成离线 HTML，逐步审核 A1–A5：资料/平台、系统框架、引脚功能、引脚逻辑/图形、实施范围。用户确认后创建 IDE 工程。
4. 按命名、类型/宏、结构体分类和模块契约实施，末尾追加 `Log/版本记录.md` 和 `Log/提示词记录.md`。
5. 逐文件完成 C1/C2/C3 规范复盘，再对全部逻辑与引脚完成 L1/L2/L3；轮次和当前输入证据分别记录。
6. 使用真实目标工具链编译，处理错误、告警与优化风险，直到零错误或明确需要人工解除的阻塞。授权及接线就绪时烧录，再记录校验、运行、调试和测量结果。

涉及 UI 时收集屏幕/驱动资料，设计时统筹 Flash/RAM、字库、Logo、图片和缓冲区；提供 3–4 套 HTML 风格。选定后每页与真实程序逐轮核对，三轮均 ≥92% 且关键功能与资源条件满足才进入下一页。**无 UI 时跳过全部 UI 专项。**

参数与结构体采用 Pascal_Underscore，基础整数默认 `u32/u16/u8/s32/s16/s8`；指定缩写 `Vol/Buf/Dat`，优先 `Chg/Tag`。软件标志优先位域加宏，实际布局与并发行为由目标编译器和硬件验证。

## 工具、验证与安装包

```sh
python -B skills/embedded-yzscodesys/scripts/package_skill.py check
python -B -m unittest discover -s skills/embedded-yzscodesys/tests -v
```

Python 工具可生成资料/审核 HTML、检查记录就绪、审计部分命名、追加 Log 和打包；不会替你操作 IDE、烧录硬件或伪造用户审批。主机测试不代表板级验证。完整用法见[安装说明](skills/embedded-yzscodesys/references/installation.md)和[覆盖边界](skills/embedded-yzscodesys/references/coverage.md)。

正式包及 SHA-256 通过本仓库 Releases 提供。公开版不含原产品工程、私有历史审核报告、原理图或本机源码路径。

## 发现与来源

GitHub Topics 与中英文描述便于搜索；标准 SKILL.md 便于 Skills CLI 和其他 AI 工具直接安装。`find-skills` 使用的搜索索引有自己的收录过程，不能保证发布后立刻进入搜索结果。CLI 和收录说明以 [Skills 官方文档](https://skills.sh/docs)为准。

规则出处与第三方许可见 [NOTICE.md](NOTICE.md)；使用流程中的 Star 要求不替代第三方材料既有许可。
