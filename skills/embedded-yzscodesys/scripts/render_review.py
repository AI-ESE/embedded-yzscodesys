#!/usr/bin/env python3
"""Render an auditable, movable, offline HTML from an embedded-project profile.

Python 3.10+; standard library only. No other project scripts are imported.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html
import io
import json
import math
from pathlib import Path, PureWindowsPath
import re
import sys
from typing import Any


PENDING = "待提供"
STAGES = (
    ("A1", "资料与平台", "核对芯片、资料版本、工具链及缺项"),
    ("A2", "程序整体框架", "核对四层职责、系统调度、数据流及初始化"),
    ("A3", "引脚功能", "逐脚核对物理封装、复用、网络与资源"),
    ("A4", "引脚逻辑与图形", "核对电平、反相链、状态转换和波形证据"),
    ("A5", "工程实施范围", "核对三轮复盘、构建优化与烧录调试范围"),
)
LABELS = {
    "schema_version": "数据格式版本", "project_name": "工程名称", "project_root": "工程根目录", "revision": "方案版本",
    "manufacturer": "芯片厂商", "part_number": "完整订货型号", "package": "具体封装", "family": "芯片系列",
    "vendor_region": "厂商地域分类", "sdk_ecosystem": "SDK 生态", "ide": "IDE", "version": "版本",
    "compiler": "编译器", "compiler_version": "编译器版本", "sdk": "SDK / lib", "sdk_version": "SDK / lib 版本",
    "optimization": "优化设置", "build_configuration": "构建组合", "kind": "类型", "original_source_path": "原代码路径",
    "original_system": "原调度系统", "system": "拟采用系统", "source_roots": "源码范围", "exclude": "排除范围及理由",
    "id": "编号", "path": "文件路径", "sha256": "SHA-256", "status": "状态", "source": "资料来源 / 证据",
    "physical_pin": "封装物理脚", "gpio": "GPIO / 复用", "function": "功能 / 用途", "net": "原理图页 / 位号 / 网络",
    "direction": "电气方向", "resources": "外设 / 时钟 / IRQ / DMA", "active_level": "有效电平", "inversion": "反相 / 隔离链",
    "pull": "上下拉 / 输出类型", "power_on_state": "上电态", "reset_state": "复位态", "run_state": "运行态 / 软件动作",
    "fault_state": "故障 / 超时态", "trigger": "采样 / 触发 / 时序条件", "code": "代码 / 拟采用接口", "review_status": "审核状态",
    "description": "说明", "requirements": "关联需求", "pin_ids": "关联引脚", "title": "标题", "caption": "图形说明",
    "name": "名称", "layer": "所属层", "responsibility": "职责", "period": "周期", "priority": "优先级",
    "stack": "任务栈", "unit": "单位", "budget": "运行预算", "interfaces": "接口", "dependencies": "依赖",
    "owner": "数据所有者", "initialization": "初始化", "failure": "失败处理", "synchronization": "同步 / 通知",
    "instrument": "测量仪器", "conditions": "模型 / 输入 / 采集条件", "constraints": "边沿 / 极性 / 约束",
    "user_evidence": "用户回复证据文件", "user_evidence_text": "用户回复文字", "user_evidence_sha256": "用户证据 SHA-256", "input_digest": "记录绑定摘要",
    "approval_digest": "方案绑定摘要", "comment": "用户意见", "scope": "确认 / 实施范围",
    "order": "执行顺序", "destination": "接收方 / 目标",
}


def plain(value: Any, missing: str = PENDING) -> str:
    if value is None or value == "" or value == [] or value == {}:
        return missing
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value)


def esc(value: Any, missing: str = PENDING) -> str:
    return html.escape(plain(value, missing), quote=True)


def mapping(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def records(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return [] if value is None else [{"description": value}]
    return [entry if isinstance(entry, dict) else {"description": entry} for entry in value]


def table(headers: list[str], rows: list[list[Any]], caption: str = "") -> str:
    if not rows:
        rows = [[PENDING] * len(headers)]
    head = "".join(f'<th scope="col">{esc(item)}</th>' for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>" for row in rows)
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    return f'<div class="table-scroll" role="region" aria-label="{esc(caption or "审核表格")}" tabindex="0"><table>{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def record_table(value: Any, preferred: tuple[str, ...] = (), caption: str = "") -> str:
    items = records(value)
    keys = list(preferred)
    for item in items:
        for key in item:
            if key not in keys:
                keys.append(key)
    if not keys:
        keys = ["description", "status"]
    return table([LABELS.get(key, key) for key in keys], [[item.get(key) for key in keys] for item in items], caption)


def key_table(value: Any, required: tuple[str, ...] = (), caption: str = "") -> str:
    item = mapping(value)
    keys = list(required) + [key for key in item if key not in required]
    return table(["登记项", "当前资料 / 记录"], [[LABELS.get(key, key), item.get(key)] for key in keys], caption)


def note(text: str, risk: bool = False) -> str:
    return f'<p class="notice{" risk" if risk else ""}">{esc(text)}</p>'


def local_file(base: Path, value: Any) -> Path:
    """Accept existing relative files contained by the profile's real directory."""
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError("文件路径待提供")
    win_path = PureWindowsPath(value)
    path = Path(value.replace("\\", "/"))
    if ":" in value or path.is_absolute() or win_path.is_absolute() or ".." in path.parts:
        raise ValueError("仅允许资料目录内的相对文件路径")
    candidate = (base / path).resolve()
    try:
        candidate.relative_to(base.resolve())
    except ValueError as error:
        raise ValueError("文件越出资料目录") from error
    if not candidate.is_file():
        raise ValueError("实际文件待提供")
    return candidate


def raster_uri(base: Path, value: Any) -> str:
    path = local_file(base, value)
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("图片超过 20 MiB，请提供适合审核的预览图")
    data = path.read_bytes()
    suffix = path.suffix.lower()
    if suffix == ".png" and len(data) >= 24 and data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR":
        mime = "image/png"
    elif suffix in (".jpg", ".jpeg") and len(data) >= 4 and data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9"):
        mime = "image/jpeg"
    elif suffix == ".gif" and len(data) >= 13 and data[:6] in (b"GIF87a", b"GIF89a"):
        mime = "image/gif"
    elif suffix == ".webp" and len(data) >= 16 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError("只嵌入文件特征匹配的 PNG / JPEG / WebP / GIF；SVG 不作为外部输入")
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def record_file(base: Path, value: Any, profile: dict, *, evidence: bool = False) -> Path:
    """Resolve workflow paths, with CSV still bounded to the profile directory.

    Workflow records may be relative to project_root or absolute under output.
    Approval proofs additionally admit files inside the declared project root.
    """
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ValueError("文件路径待提供")
    path = Path(value.replace("\\", "/"))
    if ".." in path.parts or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        raise ValueError("仅允许资料目录内的相对文件路径；工程记录不可越界")
    if ":" in value and not path.is_absolute():
        raise ValueError("工程记录路径格式需核对")
    root_value = profile.get("project_root")
    root = Path(root_value).resolve() if isinstance(root_value, str) and root_value and Path(root_value).is_absolute() else None
    roots = [base.resolve()]
    if evidence and root and root.is_dir():
        roots.append(root)
    candidates = [path] if path.is_absolute() else [base / path] + ([root / path] if root else [])
    in_scope = False
    for candidate in candidates:
        candidate = candidate.resolve()
        if not any(candidate == allowed or allowed in candidate.parents for allowed in roots):
            continue
        in_scope = True
        if candidate.is_file():
            return candidate
    raise ValueError("实际文件待提供" if in_scope else "文件越出审核资料 / 工程允许目录")


def graph_kind(item: dict, base: Path) -> str:
    kind = item.get("kind")
    if kind == "expected":
        return "设计预期／待确认"
    if kind == "simulation":
        return "仿真／待审核"
    if kind in ("measured", "measurement"):
        try:
            local_file(base, item.get("path"))
            complete = all(item.get(key) for key in ("source", "instrument", "conditions"))
        except (OSError, ValueError):
            complete = False
        return "实测资料／待审核" if complete else "实测证据待补"
    return "图形类型待确认"


def preview(uri: str, title: Any) -> str:
    return f'<a class="zoom-link" href="{esc(uri)}" target="_blank" rel="noopener" data-zoom><img src="{esc(uri)}" alt="{esc(title)}" loading="lazy"><span>放大查看</span></a>'


def waveform_uri(item: dict) -> str:
    """Draw only supplied digital samples; never invent units or timing values."""
    unit = item.get("unit")
    if not isinstance(unit, str) or not unit.strip() or len(unit) > 32:
        raise ValueError("时间单位或有效采样数据待补")
    signals = records(item.get("signals"))
    if not signals or len(signals) > 32:
        raise ValueError("时间单位或有效采样数据待补")
    values: list[list[tuple[float, int]]] = []
    for signal in signals:
        samples = signal.get("samples")
        if not isinstance(samples, list) or not 2 <= len(samples) <= 5000:
            raise ValueError("时间单位或有效采样数据待补")
        points = []
        for sample in samples:
            sample = mapping(sample)
            time, value = sample.get("t"), sample.get("value")
            if isinstance(time, bool) or not isinstance(time, (int, float)):
                raise ValueError("采样时间必须为有限数值")
            try:
                time = float(time)
            except OverflowError as error:
                raise ValueError("采样时间超出可绘制数值范围") from error
            if not math.isfinite(time):
                raise ValueError("采样时间必须为有限数值")
            if isinstance(value, bool) or value not in (0, 1) or not isinstance(value, (int, float)):
                raise ValueError("数字波形仅接受 0 / 1 采样值")
            if points and time <= points[-1][0]:
                raise ValueError("采样时间必须严格递增")
            points.append((time, int(value)))
        values.append(points)
    start = min(points[0][0] for points in values)
    end = max(points[-1][0] for points in values)
    if not math.isfinite(end - start) or end <= start:
        raise ValueError("采样时间范围无效")
    width, height = 960, 88 + 74 * len(signals)
    left, right = 150, 920
    x = lambda time: left + (time - start) / (end - start) * (right - left)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
             f'<title>{esc(item.get("title", "数字时序图"))}</title><rect width="100%" height="100%" fill="#ffffff"/>',
             '<g font-family="sans-serif" font-size="14" fill="#18334c">']
    for index in range(6):
        tick = start + (end - start) * index / 5
        tick_x = x(tick)
        parts.append(f'<path d="M{tick_x:.2f} 32 V{height - 46}" stroke="#d7e0e7"/><text x="{tick_x:.2f}" y="{height - 26}" text-anchor="middle">{tick:g}</text>')
    for index, (signal, points) in enumerate(zip(signals, values)):
        high = 43 + index * 74
        y = lambda value: high if value else high + 28
        poly = [(x(points[0][0]), y(points[0][1]))]
        previous = points[0][1]
        for time, value in points[1:]:
            poly.extend(((x(time), y(previous)), (x(time), y(value))))
            previous = value
        coordinates = " ".join(f"{px:.2f},{py:.2f}" for px, py in poly)
        parts.append(f'<text x="12" y="{high + 19}">{esc(signal.get("name"))}</text><text x="130" y="{high + 4}" font-size="10">1</text><text x="130" y="{high + 32}" font-size="10">0</text><polyline points="{coordinates}" fill="none" stroke="#215b83" stroke-width="2.5"/>')
    parts.append(f'<text x="{width // 2}" y="{height - 6}" text-anchor="middle">时间 ({esc(unit)})；边沿由提供的采样点表示</text></g></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode("".join(parts).encode("utf-8")).decode("ascii")


def graph_cards(items: Any, base: Path, waveforms: bool = False) -> str:
    cards = []
    for index, item in enumerate(records(items), 1):
        title = item.get("title") or item.get("id") or f"图形 {index}"
        try:
            uri = waveform_uri(item) if waveforms else raster_uri(base, item.get("path"))
            image = preview(uri, title)
        except (OSError, ValueError) as error:
            image = note(f"未嵌入：{error}", True)
        metadata = {key: value for key, value in item.items() if key != "signals"}
        required = ("source", "conditions", "unit", "constraints") if waveforms else ("source", "caption", "conditions")
        cards.append(f'<figure class="graph"><figcaption><strong>{esc(title)}</strong><span class="badge">{esc(graph_kind(item, base))}</span></figcaption>{image}{key_table(metadata, required, "图形条件与证据")}</figure>')
    return '<div class="graphs">' + "".join(cards) + "</div>" if cards else note("图形与信号资料待提供；当前不生成虚构引脚、电平或时序数值。")


FRAMEWORK = '''<figure class="framework"><figcaption>四层职责与依赖方向 <span class="badge">设计框架／待确认</span></figcaption>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 174" role="img" aria-label="设计框架 Task 到 APP 到 FML 到 HDL，实际模块和接口待资料核对"><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7" fill="#215b83"/></marker></defs><g fill="#edf4f9" stroke="#91aabd"><rect x="10" y="18" width="210" height="110" rx="6"/><rect x="252" y="18" width="210" height="110" rx="6"/><rect x="494" y="18" width="210" height="110" rx="6"/><rect x="736" y="18" width="210" height="110" rx="6"/></g><g font-family="sans-serif" fill="#18334c" text-anchor="middle"><g font-size="24" font-weight="700"><text x="115" y="57">Task</text><text x="357" y="57">APP</text><text x="599" y="57">FML</text><text x="841" y="57">HDL</text></g><g font-size="16"><text x="115" y="90">调度与任务入口</text><text x="357" y="90">业务条件与状态</text><text x="599" y="90">功能能力与接口</text><text x="841" y="90">芯片与硬件访问</text><text x="480" y="158">调用依赖方向；中断、快路径与数据所有权须在实际方案中单列</text></g></g><g stroke="#215b83" stroke-width="2" marker-end="url(#arrow)"><path d="M223 73H247"/><path d="M465 73H489"/><path d="M707 73H731"/></g></svg></figure>'''


def csv_review(base: Path, value: Any, title: str, profile: dict) -> str:
    try:
        path = record_file(base, value, profile)
        if path.suffix.lower() != ".csv":
            raise ValueError("请提供 CSV 审核记录")
        if path.stat().st_size > 5 * 1024 * 1024:
            raise ValueError("CSV 超过 5 MiB，需按范围拆分")
        rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig"))))
        if not rows or not rows[0]:
            raise ValueError("CSV 审核记录为空")
        if len(rows) > 10001 or len(rows[0]) > 80 or any(len(row) != len(rows[0]) for row in rows[1:]):
            raise ValueError("CSV 行列范围或结构需要核对")
        return table(rows[0], rows[1:], title)
    except (OSError, ValueError, UnicodeError, csv.Error) as error:
        return note(f"{title}：{error}；未执行的轮次不得记为通过。")


def approval_status(record: dict, revision: Any, base: Path, profile: dict) -> tuple[str, str]:
    status = record.get("status") or "待确认"
    if status == "pending":
        status = "待确认"
    if status in ("已确认", "confirmed", "approved"):
        digest = None
        try:
            if record.get("user_evidence"):
                path = record_file(base, record["user_evidence"], profile, evidence=True)
                if 0 < path.stat().st_size <= 20 * 1024 * 1024:
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
            elif isinstance(record.get("user_evidence_text"), str) and record["user_evidence_text"].strip():
                digest = hashlib.sha256(record["user_evidence_text"].encode("utf-8")).hexdigest()
        except (OSError, ValueError):
            digest = None
        valid = bool(revision) and record.get("revision") == revision
        valid = valid and bool(record.get("approval_digest") or record.get("input_digest"))
        valid = valid and digest is not None and digest == record.get("user_evidence_sha256")
        return ("记录已确认", "记录含用户证据；摘要仍由 check 准入脚本核验，HTML 不决定放行。") if valid else ("待确认", "证据或版本待核对；所填确认状态未作为有效确认显示。")
    return plain(status), "记录状态仅供审核；是否可继续实施由 check 准入脚本核验。"


def stage_html(stage: str, title: str, summary: str, body: str, profile: dict, base: Path) -> str:
    matching = [item for item in records(profile.get("approvals")) if item.get("stage") == stage]
    record = matching[-1] if matching else {}
    status, explanation = approval_status(record, profile.get("revision"), base, profile)
    if len(matching) > 1:
        status, explanation = "待确认", "同一阶段存在多条确认记录，需核对唯一适用版本与范围。"
    rows = [[status, record.get("comment") or record.get("user_evidence_text") or record.get("user_evidence"), record.get("revision") or profile.get("revision"), record.get("scope"), record.get("user_evidence_sha256"), record.get("approval_digest") or record.get("input_digest")]]
    approval = table(["记录状态", "用户意见 / 回复证据", "方案版本", "确认范围", "用户证据 SHA-256", "记录绑定摘要"], rows, "阶段审核记录")
    options = '<option value="待确认" selected>待确认</option><option value="已确认">已确认（草稿意向）</option><option value="需修改">需修改</option><option value="不适用">不适用（请说明理由）</option>'
    controls = f'<fieldset class="draft-stage" data-stage="{stage}"><legend>{stage} 用户意见草稿</legend><label for="state-{stage}">草稿状态</label><select id="state-{stage}" name="draft-status">{options}</select><label for="comment-{stage}">用户意见、范围与理由</label><textarea id="comment-{stage}" name="draft-comment" rows="2" placeholder="请填写具体条目和意见；此处填写不会生成实际授权。"></textarea></fieldset>'
    opening = " open" if stage == "A1" else ""
    return f'<details class="stage" id="{stage}" data-status="{esc(status)}"{opening}><summary><span class="stage-index">{stage}</span><span class="stage-title">{title}<small>{summary}</small></span><span class="badge">{esc(status)}</span></summary><div class="stage-body">{approval}{note(explanation)}{body}{controls}</div></details>'


def render(profile: dict, base: Path) -> str:
    """Return a complete self-contained HTML document, without mutating inputs."""
    mcu, toolchain, work, architecture, review = (mapping(profile.get(key)) for key in ("mcu", "toolchain", "work", "architecture", "review"))
    documents = records(profile.get("documents"))
    documents_registered = bool(documents) and all(all(item.get(key) for key in ("path", "version", "sha256")) for item in documents)
    missing = []
    for label, present in (
        ("完整芯片型号 / 封装", mcu.get("part_number") and mcu.get("package")),
        ("规格书 / 原理图及版本", documents_registered),
        ("IDE / 编译器 / SDK 版本", toolchain.get("ide") and toolchain.get("compiler_version") and toolchain.get("sdk_version")),
        ("工作类型 / 分析范围", work.get("kind") and work.get("source_roots")),
        ("系统框架 / 调度方案", architecture.get("summary") and work.get("system")),
        ("全封装引脚清单与资料证据", profile.get("pins")),
        ("业务逻辑与图形 / 波形", profile.get("logic") and (profile.get("diagrams") or profile.get("waveforms"))),
        ("当前构建与硬件记录", profile.get("build") and profile.get("hardware")),
    ):
        if not present:
            missing.append([label, "待提供 / 待核对", "相关决定保持待确认；继续不依赖该资料的分析"])
    missing_table = table(["缺项 / 待核对", "资料状态", "影响与后续动作"], missing, "关键资料与缺项") if missing else note("资料登记已填入；完整性、适用性和实际证据仍待逐项核对。")
    a1 = '<h3>工程与平台资料</h3>' + key_table({key: profile.get(key) for key in ("schema_version", "project_name", "project_root", "revision")})
    a1 += key_table(mcu, ("manufacturer", "part_number", "package", "family", "vendor_region", "sdk_ecosystem"), "芯片与 SDK 生态")
    a1 += key_table(toolchain, ("ide", "version", "compiler", "compiler_version", "sdk", "sdk_version", "optimization", "build_configuration"), "工具链与构建配置")
    a1 += key_table(work, ("kind", "original_source_path", "original_system", "system", "source_roots", "exclude"), "原工程与分析范围")
    a1 += record_table(profile.get("documents"), ("id", "path", "version", "sha256", "status"), "资料索引") + missing_table
    a2 = '<h3>整体架构与调度方案</h3>' + note(plain(architecture.get("summary"))) + FRAMEWORK
    a2 += note("该图仅表示 Task → APP → FML → HDL 的设计职责方向；实际模块、接口、资源预算和初始化顺序以以下材料为准。")
    architecture_tables = (
        ("original", "原框架 / 系统证据", ("description", "source", "status")),
        ("changes", "原框架与拟采用方案差异", ("description", "scope", "source", "status")),
        ("modules", "四层模块职责、接口与依赖", ("id", "layer", "responsibility", "interfaces", "dependencies", "owner", "initialization", "failure", "status")),
        ("tasks", "裸机分时 / FreeRTOS 任务及资源表", ("id", "period", "priority", "stack", "unit", "budget", "synchronization", "interfaces", "owner", "failure", "status")),
        ("interrupts", "中断、快路径、并发与故障处理", ("id", "trigger", "priority", "interfaces", "resources", "failure", "status")),
        ("data_flows", "数据流与数据所有权", ("id", "source", "destination", "owner", "synchronization", "description", "status")),
        ("initialization", "初始化顺序与失败处理", ("order", "id", "dependencies", "description", "failure", "status")),
    )
    for key, title, columns in architecture_tables:
        a2 += f"<h3>{title}</h3>" + record_table(architecture.get(key), columns, title)
    ui = mapping(architecture.get("ui"))
    if ui.get("enabled") is True:
        a2 += '<h3>UI资源与逐页审核</h3>'
        a2 += note("先取得屏幕尺寸、分辨率及驱动芯片，统筹字库、Logo和全部页面资源与Flash/RAM。3–4套风格HTML选择后逐页落地；U1/U2/U3独立对照当前HTML与程序，每轮≥92%且资源与关键功能满足才进入下一页。此处仅显示记录，不自动评分或验证通过。", True)
        a2 += key_table(ui.get("screen"), caption="屏幕与驱动资料")
        a2 += key_table(ui.get("resources"), caption="Flash / RAM与缓冲、缓存预算")
        a2 += record_table(ui.get("assets"), ("id", "category", "path", "flash_bytes", "ram_peak_bytes", "pages", "source", "status"), "字库、Logo与页面资产清单")
        a2 += key_table({key: ui.get(key) for key in ("style_count", "selected_style")}, caption="风格选择记录")
        a2 += record_table(ui.get("pages"), ("id", "title", "html", "code"), "UI页面设计与程序映射")
    a3 = '<h3>引脚功能确认</h3>' + note("核对具体封装全部物理脚，包括电源、地、NC、保留、启动、调试及未使用脚。未识别网络不得当作 NC；当前表不自动证明全封装已覆盖。", True)
    a3 += record_table(profile.get("pins"), ("id", "physical_pin", "gpio", "function", "net", "direction", "resources", "source", "review_status"), "逐引脚功能与资源证据")
    a4 = '<h3>引脚逻辑与软件动作</h3>' + note("GPIO 写入值与负载动作须沿反相、隔离和驱动链核对；不由网络名称推定有效电平。")
    a4 += record_table(profile.get("pins"), ("id", "active_level", "inversion", "pull", "power_on_state", "reset_state", "run_state", "fault_state", "trigger", "source", "code", "review_status"), "引脚电平与状态确认")
    a4 += '<h3>业务逻辑 / 状态转换</h3>' + record_table(profile.get("logic"), ("id", "description", "requirements", "source", "code", "pin_ids"), "逻辑到资料、引脚与代码映射")
    a4 += '<h3>逻辑与状态图缩略预览</h3>' + graph_cards(profile.get("diagrams"), base)
    a4 += '<h3>信号时序 / 波形缩略预览</h3>' + note("设计预期、仿真与实测分别标识。仿真需补充模型、输入和条件；实测需提供仪器、采集条件、来源及真实文件。图形显示不代表验证成功。") + graph_cards(profile.get("waveforms"), base, True)
    a5 = '<h3>实施范围与复盘证据</h3>' + key_table(work, ("kind", "original_source_path", "original_system", "system", "source_roots", "exclude"))
    a5 += note("C1 形式与基础规则；C2 语义与接口；C3 组合与遗漏。每个纳入文件逐轮记录、绑定当前摘要；SDK / 第三方按适用规则分析，预编译库内部源码不可得时明确未验证。")
    a5 += csv_review(base, review.get("inventory_path"), "逐文件 C1 / C2 / C3", profile)
    a5 += note("L1 需求 / 原理图到代码正向追踪；L2 代码到资料反向追踪；L3 上电、复位、运行、故障、并发和优化整体复核。三轮均覆盖全部逻辑与相关引脚，软件、仿真与实测分开记录。")
    a5 += csv_review(base, review.get("logic_pins_path"), "逐逻辑与引脚 L1 / L2 / L3", profile)
    a5 += csv_review(base, review.get("rule_coverage_path"), "规则覆盖矩阵与未解决项", profile)
    if ui.get("enabled") is True:
        a5 += record_table(review.get("ui_pages"), ("id", "rounds", "status"), "UI逐页U1 / U2 / U3匹配审核记录")
    a5 += note("工程搭建后维护Log/版本记录.md和Log/提示词记录.md：每条在末尾追加、空行分隔。版本关联实际修改文件，提示词关联每次精简提问和最终改善输出；不能替代C/L三轮或实测证据。")
    a5 += '<h3>目标构建、告警与优化</h3>' + note("需核对实际 IDE / 目标编译器、发布配置、优化选项、命令 / 日志 / 退出码、MAP / 反汇编与产物摘要。Debug 构建或主机检查不替代最终目标构建。")
    a5 += key_table(toolchain, ("optimization", "build_configuration"))
    a5 += key_table(profile.get("build"), ("status",), "构建记录") if isinstance(profile.get("build"), dict) else record_table(profile.get("build"), ("status",), "构建记录")
    a5 += '<h3>烧录、接线与调试观察</h3>' + note("当前目标、接线、已确认擦写范围和固件摘要须有证据；烧录成功不等于功能或波形实测通过。未采集日志保持待调试。")
    a5 += key_table(profile.get("hardware"), ("status",), "硬件与调试记录") if isinstance(profile.get("hardware"), dict) else record_table(profile.get("hardware"), ("status",), "硬件与调试记录")
    bodies = (a1, a2, a3, a4, a5)
    content = "".join(stage_html(*stage, body, profile, base) for stage, body in zip(STAGES, bodies))
    content += '<section class="continuation"><h2>继续实施前的核对</h2>' + note("逐项确认当前版本与范围，解决阻断缺项，运行 check 准入脚本核验记录绑定摘要。此 HTML 为审核材料，不自动授权搭建、改写旧代码、烧录或标记验证通过。", True) + missing_table + '</section>'
    navigation = "".join(f'<a href="#{stage}"><b>{stage}</b><span>{title}</span></a>' for stage, title, _ in STAGES)
    replacements = {"TITLE": esc(profile.get("project_name"), "待命名工程"), "REVISION": esc(profile.get("revision")), "CONTENT": content, "NAV": navigation, "PROJECT_ATTR": esc(profile.get("project_name"), "待命名工程"), "REVISION_ATTR": esc(profile.get("revision"))}
    template_path = Path(__file__).resolve().parents[1] / "assets" / "review-shell.html"
    template = template_path.read_text(encoding="utf-8")
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda found: replacements[found.group(1)], template)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成可移动、离线的单文件 HTML 工程审核册；不授予实施权限。")
    parser.add_argument("--profile", required=True, type=Path, help="UTF-8 工程 JSON；相对图像和 CSV 以此文件目录为根")
    parser.add_argument("--output", required=True, type=Path, help="输出 HTML 路径")
    args = parser.parse_args(argv)
    try:
        if args.profile.resolve() == args.output.resolve():
            raise ValueError("输出不可覆盖输入 JSON")
        data = json.loads(args.profile.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("JSON 顶层必须是对象")
        result = render(data, args.profile.resolve().parent)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    except (OSError, ValueError, UnicodeError, KeyError) as error:
        print(f"审核 HTML 未生成（JSON / 文件 / 资料错误）：{error}", file=sys.stderr)
        return 2
    print(f"HTML: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
