# 离线 HTML 工程审核册

生成器仅使用 Python 3.10+ 标准库，无网络请求，不导入本技能其他脚本。

```powershell
python -B scripts/render_review.py --profile 工程资料.json --output framework-review.html
python -B -m unittest discover -s tests -p test_render_review.py -v
```

生成后直接在浏览器打开输出 HTML。文件已内嵌样式、交互、允许的资料图和生成时序图，可单独复制到其他目录或设备阅读。源码模板位于 `assets/review-shell.html`，由生成器替换其占位；不要直接把模板当成工程审核结果。

## 输入字段

JSON 顶层为对象，UTF-8（可带 BOM）。未知值留空，页面显示“待提供”，不会补出芯片、引脚、时间单位或采样值。顶层支持：

| 字段 | 内容 |
| --- | --- |
| `schema_version`、`project_name`、`project_root`、`revision` | 资料格式、工程及方案版本 |
| `mcu` | `manufacturer, part_number, package, family, vendor_region, sdk_ecosystem` |
| `documents[]` | `id, path, version, sha256, status`；资料路径为文字登记，不自动打开 |
| `toolchain` | `ide, version, compiler, compiler_version, sdk, sdk_version, optimization, build_configuration` |
| `work` | `kind, original_source_path, original_system, system, source_roots, exclude` |
| `architecture` | `summary, modules[], tasks[], interrupts[], data_flows[]`；另外支持 `initialization[]`、`original[]`、`changes[]`；各记录任意字段均保留 |
| `pins[]` | `id, physical_pin, gpio, function, net, direction, active_level, inversion, pull, reset_state, run_state, fault_state, source, code, review_status`；可补 `power_on_state, trigger, resources` 等字段 |
| `logic[]` | `id, description, requirements, source, code, pin_ids` |
| `diagrams[]` | `id, title, kind, path, source, caption, conditions, instrument`；类型为 `expected / simulation / measured` |
| `waveforms[]` | 下述采样结构；不会从文字需求猜测数字波形 |
| `approvals[]` | `stage, status, revision, input_digest`（或 `approval_digest`）、`user_evidence` 证据文件路径、`user_evidence_sha256`；可补 `scope, comment`；仅展示文字时可显式用 `user_evidence_text` |
| `review` | `inventory_path, logic_pins_path, rule_coverage_path` 指向 CSV |
| `build`、`hardware` | 字典或字典列表，原样转义为记录表，未填不表示已执行 |

`architecture` 的任务应具体登记周期/事件、预算或优先级、栈及单位、同步、接口/数据所有者和失败处理。中断与快路径单列，初始化顺序有实际依据。裸机、FreeRTOS、原系统差异不通过目录名推断。

UI工程使用`architecture.ui.enabled=true`，登记`screen`（尺寸/像素/方向/驱动）、`resources`（Flash/RAM、已有占用、预留及缓冲/缓存）、`assets[]`（字库、Logo、图标、页面资源及存储/峰值内存）、`style_count/selected_style`和`pages[]`（页面id/title/html/code等方案映射）。U1/U2/U3证据与分项评分另存`review.ui_pages[]`或其实际报告，避免追加复盘结果改变方案摘要。框架册显示这些记录摘要；[UI流程](ui-design.md)另行设计3–4套完整风格HTML并按页对照实际程序，三轮均≥92%且资源/关键功能满足后推进。渲染器不自动计算匹配度，不把填写分数转成通过。

## 图形与波形

外部图只接受 **profile 所在目录及其子目录**中的实际 PNG、JPEG、WebP、GIF，后缀与文件特征必须匹配，每图最多 20 MiB。路径必须相对 profile 目录，拒绝远程 URL、绝对路径、`..`、越界符号链接、SVG 和伪装的图片。图形转为 data URI；原路径和来源仍作为文字显示。没有兼容图片时先将原图另行导出为实际栅格图，再运行生成器。

`review` 的 CSV 默认按 profile 目录解析，并兼容工作流生成的 `project_root` 相对路径或绝对路径，**最终文件仍必须处于 profile 目录中**。UTF-8（可带 BOM），最多 5 MiB、10,000 条数据行、80 列，列数不一致会显示问题。应先生成真实逐文件、逐逻辑/引脚、规则覆盖记录，再渲染。缺少 CSV 时显示未执行，不能拿页面中的范围说明替代三轮复盘。

以下仅示范数据结构，数值不属于任何实际工程：

```json
{
  "waveforms": [{
    "id": "用户指定信号编号",
    "title": "来自工程资料的信号标题",
    "kind": "expected",
    "unit": "来自资料的时间单位",
    "source": "资料版本/页码",
    "conditions": "模型、输入或采集条件",
    "constraints": "有效极性、边沿及约束来源",
    "signals": [{"name": "资料信号名", "samples": [{"t": 0, "value": 0}, {"t": 1, "value": 1}]}]
  }]
}
```

每个信号至少两个严格递增、有限数值的采样时间；数值只接受 0 或 1，每信号最多 5,000 点、每图最多 32 个信号。缺少单位或数据便保留待补位置，不画假图。SVG 仅由生成器从安全转义的采样值生成，无脚本或外部引用。

`expected` 显示“设计预期／待确认”；`simulation` 显示“仿真／待审核”，模型、输入及条件仍需逐项填入。`measured`（兼容 `measurement`）只有同时含 `source`、`instrument`、`conditions`，且 `path` 指向目录内真实证据文件时才显示“实测资料／待审核”，否则显示“实测证据待补”。采样波形的证据文件可以为 CSV，外部图本身仍仅接受栅格图。无论何种类型，生成器都不自动标记“已验证”。

## 状态与意见草稿

A1–A5 使用原生 `details`，默认展示摘要，可逐阶段展开，支持表格横滚、图形放大、窄屏与打印。四层 SVG 明确为设计框架；资料未定时不伪装为已实现架构。

已有 `approvals` 记录展示其版本、范围、证据及摘要。`user_evidence` 按真实证据文件处理：允许 profile 目录或显式 `project_root` 内的非空文件（上限 20 MiB），按文件字节验证 SHA-256；相对路径先从 profile 目录、再从工程根目录寻找，拒绝 `..`、远程 URL 和边界外文件。所填“已确认”只有在当前版本一致、存在非空绑定摘要、证据 SHA-256 匹配时才显示“记录已确认”；否则保持“待确认”。仅为展示内联回复文字时，须显式使用 `user_evidence_text` 并填文字 UTF-8 SHA-256，这不会转换为准入脚本要求的证据文件。同一阶段有多条记录时提示冲突。**这只是展示层证据检查，当前方案摘要是否一致、是否允许实施仍由 `check` 准入脚本核验**；生成器不复用或猜测其他脚本的摘要算法，也不授予实施权限。

每阶段的用户意见控件初始均为“待确认”，和记录状态分开。“导出审核意见草稿”只下载 `review-opinions-draft.json`，含 `document_type: embedded_review_opinion_draft`、`draft: true`、`authorization_obtained: false` 与 `opinions[]`。它不含可直接写回的 `approvals` 集合，不修改 profile，不产生授权，不写浏览器持久存储。用户实际回复后再由工程记录流程核对版本/范围并登记证据。

页面无需 JavaScript 即可阅读全部材料并手动展开。JavaScript 仅用于全部展开/收起、打印展开、data URI 图形弹窗和下载草稿。无 CDN、远程字体、远程脚本、文件回写或网络提交。
