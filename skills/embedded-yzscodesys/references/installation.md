# 嵌入式工程师：添加、调用与维护

Skill标识为`embedded-yzscodesys`，中文显示名为“嵌入式工程师”，调用名称为`$embedded-yzscodesys`。分发包名为`embedded-yzscodesys-1.1.0.zip`；解压后的顶层文件夹必须为`embedded-yzscodesys`。

使用前须按[仓库说明](repository-policy.md)，在真实来源仓库手动 Star 并明确确认。当前发布状态及准确地址见[发行信息](../assets/distribution.json)；仓库待发布时如实说明，不把安装完成当作已经 Star。

## 从 GitHub 安装

来源仓库：[AI-ESE/embedded-yzscodesys](https://github.com/AI-ESE/embedded-yzscodesys)。远程发布完成后，可使用 Skills CLI 发现和安装：

```text
npx skills add AI-ESE/embedded-yzscodesys --list
npx skills add AI-ESE/embedded-yzscodesys --skill embedded-yzscodesys
```

适用于支持 SKILL.md 的 Codex、Claude Code、Cursor、GitHub Copilot 等工具，安装时选择实际使用的 AI 工具。也可只复制仓库中的 `skills/embedded-yzscodesys` 文件夹到工具支持的 Skill 发现目录。

GitHub 可见、CLI 可直接安装、搜索服务收录是不同状态；公开和安装成功不代表所有搜索索引已立即更新。CLI 用法及遥测说明见 [Skills 官方文档](https://skills.sh/docs/cli)。

## 包内容与前提

解压ZIP得到`embedded-yzscodesys/`：SKILL.md是入口，agents/openai.yaml是界面元数据，references保存规则和流程说明，assets保存模板，scripts提供工具，tests验证工具。脚本使用Python 3.10+标准库，目标编译、EDA、烧录和调试由实际工程环境提供。

find-skills、Superpowers、embedded-systems及EDA/PDF能力有则按阶段使用；本包不复制这些第三方Skill，也不强制安装全部辅助技能。新能力核对来源和支持范围，缺关键工具时说明待处理项。

涉及UI的项目另按[UI专项](ui-design.md)核对用户指定8项Skill，已可用的不重复安装，缺项核对来源后补装；无UI则整组UI专项跳过。该要求不改变普通固件项目的安装前提。

## Windows用户安装

按[官方本地Skill目录说明](https://learn.chatgpt.com/docs/build-skills)，个人目录为用户主目录下`.agents/skills`，项目可使用工程内`.agents/skills`。在包含解压后`embedded-yzscodesys`文件夹的目录运行：

```powershell
$skillSource = (Resolve-Path -LiteralPath '.\embedded-yzscodesys').Path
$installParent = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.agents\skills'
$installTarget = Join-Path $installParent 'embedded-yzscodesys'
if (Test-Path -LiteralPath $installTarget) { throw '同名Skill已存在，请先核对和备份旧版本。' }
New-Item -ItemType Directory -Force -Path $installParent | Out-Null
Copy-Item -LiteralPath $skillSource -Destination $installParent -Recurse
```

从本资料工作区安装时先进入其`skills`目录。项目安装则把installParent改为目标工程内`.agents\skills`。只选一个作用域放同名Skill，避免选择器出现多个相同名称。

旧版环境使用其他目录时先查其实际发现位置，不重复安装。Codex通常会检测Skill变化；没出现时重启并重新打开会话，以实际加载列表确认。

从旧名称副本迁移时，先保留其中的本地修改，再将旧副本移出实际发现目录，按新名称安装并确认加载列表；避免两份相同内容以不同名称同时被发现。本工作区的重命名和打包不会修改已安装的全局目录。


## 调用

新建工程：

```text
使用 $embedded-yzscodesys 新建嵌入式工程。
芯片/封装：……；规格书：……；原理图：……；IDE版本：……；SDK/例程：……。
先分析资料并输出HTML框架、引脚功能与逻辑/波形审核表，我确认后再搭工程。
```

重构/移植：

```text
使用 $embedded-yzscodesys，原代码路径是……，目标芯片和IDE是……。
先分析原系统与数据归属，保留必须保持的行为，再输出方案让我逐步审核。
```

接续时提供project-profile.json、审核证据和记录目录，校验当前阶段后继续。也可在具体工程上下文单独请求规范、结构体或宏配置检查。

## 工具验证

在Skill目录中运行：

```text
python -B scripts/project_workflow.py --help
python -B scripts/render_review.py --help
python -B scripts/audit_naming.py --help
python -B scripts/package_skill.py check
python -B -m unittest discover -s tests -v
```

初始化不会产生通过记录。详细填写方法见[运行指南](operation.md)、[字段说明](profile-schema.md)、[HTML说明](html-review.md)。

## 更新和打包

先在工作目录改规则、工具、模板并测试，再在新位置验证解压包。已安装目录有本地改动时保留旧副本/摘要，验证新版本后再更新，不覆盖未知文件。

```text
python -B scripts/package_skill.py pack --output <Skill目录外的新ZIP路径>
```

工具拒绝覆盖已有ZIP或把ZIP放进自身目录；package-manifest.json记录文件摘要。修改后重新打包，不沿用旧摘要。安装后的Skill用于之后的调用，已有工程仍核对当前规则与证据。

本次交付提供安装文件和说明；全局安装由实际使用者按所选作用域执行。IDE、器件包、SDK和调试驱动按具体工程配置。
