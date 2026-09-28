from __future__ import annotations

import base64
import math
import mimetypes
import re
import time
from datetime import datetime, timezone
from html import escape as html_escape
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup


ROOT = Path(__file__).parent
STATUS_ROOT = ROOT / "status_source" / "apps" / "status"
TEMPLATE_ROOT = ROOT / "templates"


ICON_PATHS = {
    "activity": '<path d="M3 12h4l3-9 4 18 3-9h4"/>',
    "arrow-down": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    "arrow-up": '<path d="M12 19V5"/><path d="m5 12 7-7 7 7"/>',
    "arrow-up-right": '<path d="M7 17 17 7"/><path d="M7 7h10v10"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "circle-alert": '<circle cx="12" cy="12" r="9"/><path d="M12 8v5"/><path d="M12 16h.01"/>',
    "circle-help": '<circle cx="12" cy="12" r="9"/><path d="M9.6 9a2.5 2.5 0 1 1 4.4 1.65c-.9.9-2 1.25-2 2.85"/><path d="M12 16h.01"/>',
    "circle-check": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.3 2.3 4.7-4.8"/>',
    "circle-x": '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6"/><path d="m15 9-6 6"/>',
    "cpu": '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="8" y="8" width="8" height="8"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M20 9h3M20 14h3M1 9h3M1 14h3"/>',
    "database": '<ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5"/><path d="M5 12v7c0 1.7 3.1 3 7 3s7-1.3 7-3v-7"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.3 2.5 3.3 5.5 3.3 9s-1 6.5-3.3 9c-2.3-2.5-3.3-5.5-3.3-9S9.7 5.5 12 3Z"/>',
    "hard-drive": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M7 15h.01M11 15h.01"/>',
    "languages": '<path d="m5 8 4 8M3 16l4-8 4 8M4.5 13h5"/><path d="M13 6h8M17 4v2c0 5-2.3 8-6 10M14 11c1.3 1.5 3 2.7 5 3.5"/>',
    "radio": '<circle cx="12" cy="12" r="2"/><path d="M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8"/>',
    "refresh": '<path d="M20 11a8 8 0 0 0-14.8-4L3 10"/><path d="M3 4v6h6"/><path d="M4 13a8 8 0 0 0 14.8 4L21 14"/><path d="M21 20v-6h-6"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>',
    "wifi": '<path d="M5 13a10 10 0 0 1 14 0M8 16a6 6 0 0 1 8 0M11 19a2 2 0 0 1 2 0"/>',
}


DEVICE_LABELS = {
    "yourtj-app": "YourTJ App",
    "mobile": "手机",
    "laptop": "笔记本",
    "desktop": "台式机",
    "tablet": "平板",
    "other": "其他",
    "unknown": "未识别",
    "windows": "Windows",
    "macos": "macOS",
    "ios": "iOS",
    "android": "Android",
    "linux": "Linux",
    "chromeos": "ChromeOS",
    "chrome": "Chrome",
    "edge": "Edge",
    "safari": "Safari",
    "firefox": "Firefox",
    "webview": "内嵌浏览器",
    "opera": "Opera",
    "samsung": "Samsung Internet",
}
DEVICE_PALETTE = {
    "yourtj-app": "#df795e",
    "mobile": "#27a99a",
    "laptop": "#5987db",
    "desktop": "#c79953",
    "tablet": "#a18bce",
    "windows": "#5987db",
    "android": "#27a99a",
    "ios": "#8d8dcb",
    "macos": "#b38a67",
    "linux": "#bf9c43",
    "chromeos": "#73a483",
    "chrome": "#5987db",
    "edge": "#27a99a",
    "safari": "#8d8dcb",
    "webview": "#b38a67",
    "firefox": "#ca8659",
    "other": "#929cae",
    "unknown": "#a6abb5",
}


def icon(name: str, size: int = 16, stroke: float = 1.8) -> Markup:
    body = ICON_PATHS.get(name, ICON_PATHS["circle-help"])
    return Markup(f'<svg class="icon" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{body}</svg>')


def _data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _age_seconds(value: str | None, now: float) -> float:
    parsed = _parse_time(value)
    return float("inf") if parsed is None else now - parsed.timestamp()


def _fresh(value: str | None, now: float, max_age: int) -> bool:
    age = _age_seconds(value, now)
    return -60 <= age <= max_age


def _source_state(source: dict[str, Any] | None, now: float, freshness: int = 150) -> str:
    if not source:
        return "unavailable"
    state = source.get("state")
    if state == "unconfigured":
        return state
    if state == "ok" and _fresh(source.get("fetchedAt"), now, freshness):
        return "ok"
    if state in {"ok", "stale"}:
        return "stale"
    return "unavailable"


def _source_text(state: str) -> str:
    return {"ok": "已连接", "stale": "数据已过期", "unavailable": "暂时不可用", "unconfigured": "尚未连接"}.get(state, "暂时不可用")


def _badge(state: str) -> str:
    return "connected" if state == "ok" else ""


def _number(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):,.1f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return "—"


def _percent(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return "—"


def _bytes(value: Any) -> str:
    if value is None:
        return "—"
    try:
        raw = float(value)
    except (TypeError, ValueError):
        return "—"
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    index = min(int(math.log(raw, 1024)) if raw > 0 else 0, len(units) - 1)
    return f"{raw / 1024 ** index:.1f} {units[index]}" if index else f"{raw:.0f} B"


def _duration(value: Any, long: bool = False) -> str:
    if value is None:
        return "—"
    try:
        seconds = max(0, int(float(value)))
    except (TypeError, ValueError):
        return "—"
    if long and seconds >= 86_400:
        return f"{seconds // 86_400} 天 {(seconds % 86_400) // 3_600} 小时"
    if long and seconds >= 3_600:
        return f"{seconds // 3_600} 小时"
    return f"{seconds // 60} 分 {seconds % 60} 秒"


def _date_time(value: str | None) -> str:
    parsed = _parse_time(value)
    if not parsed:
        return "—"
    local = parsed.astimezone()
    return f"{local.month}月{local.day}日 {local:%H:%M:%S}"


def _short_date(value: str | None) -> str:
    parsed = _parse_time(value)
    if not parsed:
        return "—"
    local = parsed.astimezone()
    return f"{local.month}/{local.day} {local:%H:%M}"


def _usage(used: Any, total: Any) -> float | None:
    try:
        return min(100.0, max(0.0, float(used) / float(total) * 100)) if float(total) else None
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _fmt_amount(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f}%"


def _monitor_state(monitor: dict[str, Any], source_ok: bool, now: float) -> str:
    current = monitor.get("current") or {}
    if not source_ok or not _fresh(current.get("time"), now, 300):
        return "unknown"
    return str(current.get("status") or "unknown")


def _monitor_text(state: str) -> str:
    return {"up": "可访问", "down": "访问异常", "pending": "待确认", "maintenance": "维护中", "unknown": "状态未知"}.get(state, "状态未知")


def _status_signal(result: dict[str, Any], now: float) -> dict[str, str]:
    uptime = result.get("uptime") or {}
    uptime_state = _source_state(uptime, now)
    monitors = (uptime.get("data") or {}).get("monitors") or []
    monitor_states = [_monitor_state(item, uptime_state == "ok", now) for item in monitors]
    if monitor_states:
        if all(item == "up" for item in monitor_states):
            return {"text": "所有公开服务正常", "tone": "ok", "icon": "circle-check"}
        if any(item == "down" for item in monitor_states):
            return {"text": "服务异常" if all(item == "down" for item in monitor_states) else "部分服务异常", "tone": "error" if all(item == "down" for item in monitor_states) else "warning", "icon": "circle-x" if all(item == "down" for item in monitor_states) else "circle-alert"}
        if any(item == "unknown" for item in monitor_states):
            return {"text": "暂无法确认状态", "tone": "muted", "icon": "circle-help"}
        if any(item == "maintenance" for item in monitor_states):
            return {"text": "服务维护中", "tone": "warning", "icon": "circle-alert"}
        return {"text": "服务状态确认中", "tone": "warning", "icon": "circle-alert"}
    server = result.get("server") or {}
    current = (server.get("data") or {}).get("current") or {}
    if _source_state(server, now) == "ok" and _fresh(current.get("observedAt"), now, 150):
        return {"text": "服务器探针正常", "tone": "ok", "icon": "circle-check"}
    if _source_state(server, now) == "ok":
        return {"text": "服务器探针暂无新数据", "tone": "warning", "icon": "circle-alert"}
    return {"text": "暂无法确认状态", "tone": "muted", "icon": "circle-help"}


def _traffic_chart(traffic: dict[str, Any]) -> str:
    series = traffic.get("series") or []
    if not traffic.get("seriesAvailable") or not series:
        return f'<div class="status-chart-empty">{icon("activity", 26, 1.3)}<span>趋势数据暂不可用</span></div>'
    start = _parse_time(traffic.get("startAt"))
    end = _parse_time(traffic.get("endAt"))
    if not start or not end:
        return f'<div class="status-chart-empty">{icon("activity", 26, 1.3)}<span>趋势数据暂不可用</span></div>'
    step = 3_600
    first_ts = int(start.timestamp()) // step * step
    end_ts = end.timestamp()
    values = {int(_parse_time(point.get("time")).timestamp()): point for point in series if _parse_time(point.get("time"))}
    points: list[dict[str, Any]] = []
    cursor = first_ts
    while cursor <= end_ts and len(points) < 32:
        point = values.get(cursor) or {"time": datetime.fromtimestamp(cursor, timezone.utc).isoformat(), "pageviews": 0, "visitors": 0}
        points.append(point)
        cursor += step
    maximum = max(1, *(max(float(point.get("pageviews") or 0), float(point.get("visitors") or 0)) for point in points))
    bars = []
    for point in points:
        views = min(100, float(point.get("pageviews") or 0) / maximum * 100)
        visitors = min(100, float(point.get("visitors") or 0) / maximum * 100)
        bars.append(f'<div class="chart-bucket"><span class="bar bar-views" style="height:{views:.2f}%"></span><span class="bar bar-visitors" style="height:{visitors:.2f}%"></span></div>')
    mid = datetime.fromtimestamp((start.timestamp() + end.timestamp()) / 2, timezone.utc).isoformat()
    return f'<div class="traffic-chart"><div class="chart-y-axis" aria-hidden="true"><span>{_number(maximum)}</span><span>{_number(round(maximum / 2))}</span><span>0</span></div><div class="chart-plot"><div class="chart-bars">{"".join(bars)}</div><div class="chart-x-axis" aria-hidden="true"><span>{_short_date(traffic.get("startAt"))}</span><span>{_short_date(mid)}</span><span>{_short_date(traffic.get("endAt"))}</span></div></div></div>'


def _resource_chart(server: dict[str, Any]) -> str:
    points = server.get("history") or []
    if not server.get("historyAvailable") or not points:
        return f'<div class="status-chart-empty">{icon("activity", 26, 1.3)}<span>趋势数据暂不可用</span></div>'
    end = _parse_time(server.get("historyFetchedAt") or server.get("fetchedAt")) or _parse_time(points[-1].get("time"))
    if not end:
        return f'<div class="status-chart-empty">{icon("activity", 26, 1.3)}<span>趋势数据暂不可用</span></div>'
    span = 3_600
    start_ts = end.timestamp() - span

    def numeric(point: dict[str, Any], key: str) -> float:
        try:
            return float(point.get(key) or 0)
        except (TypeError, ValueError):
            return 0.0

    def x(point: dict[str, Any]) -> float:
        parsed = _parse_time(point.get("time"))
        return max(0.0, min(720.0, ((parsed.timestamp() if parsed else start_ts) - start_ts) / span * 720))

    def scale(key: str) -> tuple[float, float]:
        values = [numeric(point, key) for point in points]
        minimum, maximum = min(values, default=0), max(values, default=1)
        spread = max(maximum - minimum, 1)
        padding = max(spread * 0.16, 0.5)
        return max(0, minimum - padding), min(100, maximum + padding)

    scales = {"cpu": scale("cpu"), "memoryPercent": scale("memoryPercent")}

    def y(value: float, key: str) -> float:
        minimum, maximum = scales[key]
        return 160 - (value - minimum) / max(maximum - minimum, 0.001) * 150

    def starts(index: int) -> bool:
        if index == 0:
            return True
        previous = _parse_time(points[index - 1].get("time"))
        current = _parse_time(points[index].get("time"))
        return not previous or not current or current.timestamp() - previous.timestamp() > max(120, span / 119 * 2)

    def line(key: str) -> str:
        return " ".join(f'{"M" if starts(index) else "L"}{x(point):.2f},{y(numeric(point, key), key):.2f}' for index, point in enumerate(points))

    def area(key: str) -> str:
        result: list[str] = []
        segment: list[dict[str, Any]] = []

        def close() -> None:
            nonlocal segment
            if segment:
                first, last = segment[0], segment[-1]
                result.append(f'M{x(first):.2f},160 L{" L".join(f"{x(point):.2f},{y(numeric(point, key), key):.2f}" for point in segment)} L{x(last):.2f},160 Z')
                segment = []

        for index, point in enumerate(points):
            if starts(index):
                close()
            segment.append(point)
        close()
        return " ".join(result)

    cpu_labels = [f"{value:.1f}%" if scales["cpu"][1] - scales["cpu"][0] < 10 else f"{value:.0f}%" for value in (scales["cpu"][1], sum(scales["cpu"]) / 2, scales["cpu"][0])]
    memory_labels = [f"{value:.1f}%" if scales["memoryPercent"][1] - scales["memoryPercent"][0] < 10 else f"{value:.0f}%" for value in (scales["memoryPercent"][1], sum(scales["memoryPercent"]) / 2, scales["memoryPercent"][0])]
    svg = f'<svg viewBox="0 0 720 170" preserveAspectRatio="none" aria-hidden="true"><defs><linearGradient id="resource-memory-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="var(--gf-color-accent)" stop-opacity=".17"/><stop offset="100%" stop-color="var(--gf-color-accent)" stop-opacity="0"/></linearGradient><linearGradient id="resource-cpu-area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="var(--gf-color-primary)" stop-opacity=".18"/><stop offset="100%" stop-color="var(--gf-color-primary)" stop-opacity="0"/></linearGradient></defs><path d="{area("memoryPercent")}" class="resource-area memory-area"/><path d="{area("cpu")}" class="resource-area cpu-area"/><line x1="0" x2="720" y1="80" y2="80" class="grid-line grid-line-horizontal"/><line x1="0" x2="720" y1="10" y2="10" class="grid-line grid-line-horizontal"/><line x1="0" x2="720" y1="150" y2="150" class="grid-line grid-line-horizontal"/><line x1="0" x2="0" y1="10" y2="160" class="grid-line grid-line-vertical"/><line x1="180" x2="180" y1="10" y2="160" class="grid-line grid-line-vertical"/><line x1="360" x2="360" y1="10" y2="160" class="grid-line grid-line-vertical"/><line x1="540" x2="540" y1="10" y2="160" class="grid-line grid-line-vertical"/><line x1="720" x2="720" y1="10" y2="160" class="grid-line grid-line-vertical"/><path d="{line("memoryPercent")}" class="memory-line"/><path d="{line("cpu")}" class="cpu-line"/></svg>'
    return f'<div class="resource-history"><div class="resource-axis resource-axis-cpu"><span>{cpu_labels[0]}</span><span>{cpu_labels[1]}</span><span>{cpu_labels[2]}</span></div><div class="resource-plot">{svg}<div class="resource-ticks"><span>{_short_date(datetime.fromtimestamp(start_ts, timezone.utc).isoformat())}</span><span>{_short_date(datetime.fromtimestamp(start_ts + span / 2, timezone.utc).isoformat())}</span><span>{_short_date(end.isoformat())}</span></div></div><div class="resource-axis resource-axis-memory"><span>{memory_labels[0]}</span><span>{memory_labels[1]}</span><span>{memory_labels[2]}</span></div></div>'


def _device_chart(data: dict[str, Any], width: int = 1040) -> str:
    rows = data.get("rows") or []
    visitors = max(0.0, float(data.get("visitors") or 0))
    dimensions = ("device", "os", "browser")
    if not rows or not visitors:
        return f'<div class="status-chart-empty device-empty">{icon("users", 26, 1.3)}<span>设备分布暂不可用</span></div>'

    totals: dict[str, dict[str, float]] = {dimension: {} for dimension in dimensions}
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        try:
            value = max(0.0, float(row.get("visitors") or 0))
        except (AttributeError, TypeError, ValueError):
            continue
        if not value:
            continue
        normalized = {dimension: str(row.get(dimension) or "unknown") for dimension in dimensions}
        normalized["visitors"] = value
        normalized_rows.append(normalized)
        for dimension in dimensions:
            category = normalized[dimension]
            totals[dimension][category] = totals[dimension].get(category, 0.0) + value
    if not normalized_rows:
        return f'<div class="status-chart-empty device-empty">{icon("users", 26, 1.3)}<span>设备分布暂不可用</span></div>'

    keep: dict[str, set[str]] = {}
    for dimension in dimensions:
        ordered = sorted(totals[dimension].items(), key=lambda item: (-item[1], item[0]))
        keep[dimension] = {
            name
            for index, (name, value) in enumerate(ordered)
            if dimension == "device" or name in {"unknown", "yourtj-app"} or (index < 5 and value >= visitors * 0.015)
        }

    nodes: dict[str, dict[str, Any]] = {}
    links: dict[str, dict[str, Any]] = {}
    for row in normalized_rows:
        ids = []
        for dimension in dimensions:
            category = row[dimension] if row[dimension] in keep[dimension] else "other"
            node_id = f"{dimension}:{category}"
            nodes.setdefault(node_id, {"id": node_id, "dimension": dimension, "category": category, "value": 0.0})
            nodes[node_id]["value"] += row["visitors"]
            ids.append(node_id)
        for index in range(1, len(ids)):
            link_id = f"{ids[index - 1]}/{ids[index]}"
            link = links.setdefault(link_id, {"id": link_id, "source": ids[index - 1], "target": ids[index], "value": 0.0})
            link["value"] += row["visitors"]
    if not links:
        return f'<div class="status-chart-empty device-empty">{icon("users", 26, 1.3)}<span>设备分布暂不可用</span></div>'

    chart_top, chart_bottom = 14.0, 306.0
    node_width, node_padding = 8.0, 30.0
    columns = [[node for node in nodes.values() if node["dimension"] == dimension] for dimension in dimensions]
    positions: dict[str, dict[str, float]] = {}
    for depth, column in enumerate(columns):
        column.sort(key=lambda node: (-node["value"], node["id"]))
        total = sum(node["value"] for node in column)
        scale = max(0.5, (chart_bottom - chart_top - node_padding * max(0, len(column) - 1)) / total) if total else 0.5
        y = chart_top
        x = 102.0 + (width - 216.0) * depth / 2
        for node in column:
            height = max(1.0, node["value"] * scale)
            positions[node["id"]] = {"x0": x, "x1": x + node_width, "y0": y, "y1": y + height, "depth": float(depth), "scale": scale}
            y += height + node_padding

    source_offsets = {node_id: 0.0 for node_id in nodes}
    target_offsets = {node_id: 0.0 for node_id in nodes}
    link_markup: list[str] = []
    for index, link in enumerate(sorted(links.values(), key=lambda item: item["id"])):
        source = positions[link["source"]]
        target = positions[link["target"]]
        source_scale = source["scale"]
        target_scale = target["scale"]
        link_width = max(1.0, link["value"] * min(source_scale, target_scale))
        source_y = source["y0"] + source_offsets[link["source"]] + link_width / 2
        target_y = target["y0"] + target_offsets[link["target"]] + link_width / 2
        source_offsets[link["source"]] += link_width
        target_offsets[link["target"]] += link_width
        middle = (source["x1"] + target["x0"]) / 2
        source_color = DEVICE_PALETTE.get(nodes[link["source"]]["category"], "#929cae")
        target_color = DEVICE_PALETTE.get(nodes[link["target"]]["category"], "#929cae")
        path = f"M {source['x1']:.2f},{source_y:.2f} C {middle:.2f},{source_y:.2f} {middle:.2f},{target_y:.2f} {target['x0']:.2f},{target_y:.2f}"
        gradient_id = f"device-gradient-{index}"
        link_markup.append(
            f'<linearGradient id="{gradient_id}" gradientUnits="userSpaceOnUse" x1="{source["x1"]:.2f}" x2="{target["x0"]:.2f}"><stop offset="0%" stop-color="{source_color}"/><stop offset="100%" stop-color="{target_color}"/></linearGradient>'
        )
        name = f"{DEVICE_LABELS.get(nodes[link['source']]['category'], '其他')} → {DEVICE_LABELS.get(nodes[link['target']]['category'], '其他')}"
        link_markup.append(
            f'<g class="device-flow" role="img" aria-label="{html_escape(name)}：{_number(link["value"])} 位访客"><path d="{path}" stroke="url(#{gradient_id})" stroke-width="{link_width:.2f}" class="flow-ribbon"/><path d="{path}" stroke="transparent" stroke-width="{max(link_width, 10):.2f}" class="flow-hit"/></g>'
        )

    node_markup: list[str] = []
    for node in sorted(nodes.values(), key=lambda item: item["id"]):
        position = positions[node["id"]]
        label = DEVICE_LABELS.get(node["category"], "其他")
        label_x = position["x0"] - 12 if position["depth"] == 0 else position["x1"] + 12
        anchor = "end" if position["depth"] == 0 else "start"
        node_markup.append(
            f'<g class="device-node" role="img" aria-label="{html_escape(label)}：{_number(node["value"])} 位访客"><rect x="{position["x0"]:.2f}" y="{position["y0"]:.2f}" width="{node_width:.2f}" height="{max(1.0, position["y1"] - position["y0"]):.2f}" rx="2" fill="{DEVICE_PALETTE.get(node["category"], "#929cae")}"/><text x="{label_x:.2f}" y="{(position["y0"] + position["y1"]) / 2 - 2:.2f}" text-anchor="{anchor}">{html_escape(label)}<tspan x="{label_x:.2f}" dy="16" class="node-count">{_number(node["value"])} · {_percent(node["value"] / visitors * 100)}</tspan></text></g>'
        )

    columns_markup = "".join(f"<span>{label}</span>" for label in ("设备", "操作系统", "客户端"))
    svg = f'<svg class="device-sankey" viewBox="0 0 {width} 320" role="group" aria-label="设备、操作系统与客户端的访客分布桑基图"><defs>{"".join(item for item in link_markup if item.startswith("<linearGradient") )}</defs>{"".join(item for item in link_markup if item.startswith("<g"))}{"".join(node_markup)}</svg>'
    return f'<div class="device-chart"><div class="device-columns">{columns_markup}</div>{svg}<div class="device-detail"><span class="device-hint">悬停或聚焦节点与流线，查看人数与占比</span></div></div>'


def _styles() -> str:
    files = [STATUS_ROOT / "src" / "styles" / "tokens.css", STATUS_ROOT / "src" / "styles" / "app.css"]
    files.extend([
        STATUS_ROOT / "src" / "components" / "PageHeader.vue",
        STATUS_ROOT / "src" / "StatusPage.vue",
        STATUS_ROOT / "src" / "components" / "StatusUptime.vue",
        STATUS_ROOT / "src" / "components" / "StatusTrafficChart.vue",
        STATUS_ROOT / "src" / "components" / "StatusResourceChart.vue",
        STATUS_ROOT / "src" / "components" / "StatusDeviceChart.vue",
    ])
    chunks: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".vue":
            text = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", text, re.S))
        text = text.replace("@import './tokens.css';", "")
        text = re.sub(r":deep\(([^()]*)\)", r"\1", text)
        chunks.append(text)
    chunks.append("""
html, body { width: 1120px; min-width: 1120px; min-height: 0; height: auto; margin: 0; background: transparent; }
.status-poster { position: relative; width: 1120px; min-height: 0; height: auto; overflow: hidden; padding: 22px 32px 0; background: transparent; isolation: isolate; }
.status-poster::before { content: ''; position: absolute; inset: -28px; z-index: -2; background-image: var(--poster-background); background-size: cover; background-position: center; filter: blur(10px) saturate(1.05); opacity: .72; transform: scale(1.06); }
.status-poster::after { content: ''; position: absolute; inset: 0; z-index: -1; background: linear-gradient(180deg, rgb(250 251 253 / .38), rgb(248 250 252 / .54)); }
.status-poster .site-nav { justify-content: center; }
.status-poster .brand { margin-inline: auto; }
.status-poster .site-shell { max-width: none; min-height: 0; padding: 0; }
.status-poster .status-page { max-width: 1120px; padding-bottom: 24px; }
.status-poster .status-hero { background: color-mix(in oklch, var(--gf-color-base-100) 78%, transparent); -webkit-backdrop-filter: blur(4px); backdrop-filter: blur(4px); }
.status-poster .status-panel { background: color-mix(in oklch, var(--gf-color-base-100) 72%, transparent); -webkit-backdrop-filter: blur(3px); backdrop-filter: blur(3px); }
.status-poster .status-hero { box-shadow: inset 0 1px 0 rgb(255 255 255 / .35), 0 8px 22px -14px rgb(13 21 38 / .35); }
.status-poster .status-panel { box-shadow: inset 0 1px 0 rgb(255 255 255 / .28), 0 8px 22px -14px rgb(13 21 38 / .28); }
.status-poster .heartbeat-beat { display: block; flex: 1; min-width: 0; height: 28px; border-radius: 5px; background: var(--check-color); opacity: .72; }
.status-poster .icon { display: block; flex: 0 0 auto; }
@media (prefers-reduced-transparency: reduce) { .status-poster::before { filter: none; opacity: .12; } .status-poster .status-hero, .status-poster .status-panel { -webkit-backdrop-filter: none; backdrop-filter: none; } }
""")
    return "\n".join(chunks)


def build_poster_html(snapshot: dict[str, Any], background: bytes, background_mime: str) -> str:
    result = snapshot.get("result") or {}
    now = time.time()
    server_source = result.get("server") or {}
    traffic_source = result.get("traffic") or {}
    uptime_source = result.get("uptime") or {}
    devices_source = result.get("devices") or {}
    server_state = _source_state(server_source, now)
    traffic_state = _source_state(traffic_source, now, 600)
    uptime_state = _source_state(uptime_source, now)
    devices_state = _source_state(devices_source, now, 600)
    server = server_source.get("data") or {}
    current = server.get("current") or {}
    traffic_raw = traffic_source.get("data") or {}
    uptime_raw = uptime_source.get("data") or {}
    devices_raw = devices_source.get("data") or {}

    def src_item(key: str, name: str, logo: str, state: str) -> dict[str, str]:
        source_class = "status-ok" if state == "ok" else "status-muted"
        if key == "uptime" and any(_monitor_state(item, state == "ok", now) == "down" for item in uptime_raw.get("monitors") or []):
            source_class = "status-problem"
        return {"key": key, "name": name, "logo": logo, "class_name": source_class, "text": _source_text(state)}

    server_name = str(server.get("name") or "节点")
    resources = []
    cpu = current.get("cpu")
    memory = _usage(current.get("memoryUsed"), current.get("memoryTotal"))
    disk = _usage(current.get("diskUsed"), current.get("diskTotal"))
    for key, label, value, amount, detail, icon_name in (
        ("cpu", "CPU 使用率", _percent(cpu), _safe_float(cpu), f"{server.get('cpuCores', '—')} 核", "cpu"),
        ("memory", "内存使用", _fmt_amount(memory), memory, f"{_bytes(current.get('memoryUsed'))} / {_bytes(current.get('memoryTotal'))}", "database"),
        ("disk", "磁盘使用", _fmt_amount(disk), disk, f"{_bytes(current.get('diskUsed'))} / {_bytes(current.get('diskTotal'))}", "hard-drive"),
    ):
        resources.append({"key": key, "label": label, "value": value, "amount": f"{min(100, max(0, amount or 0)):.1f}", "high": (amount or 0) >= 85, "detail": detail, "icon": icon_name})

    traffic = {
        "visitors": _number(traffic_raw.get("visitors")),
        "pageviews": _number(traffic_raw.get("pageviews")),
        "active_visitors": _number(traffic_raw.get("activeVisitors")),
        "visits": _number(traffic_raw.get("visits")),
        "bounce": _percent(traffic_raw.get("bounceRate")),
        "duration": _duration(traffic_raw.get("averageDuration")),
        "partial": traffic_raw.get("activeVisitors") is None or not traffic_raw.get("seriesAvailable"),
        "badge": _badge(traffic_state),
        "source_text": _source_text(traffic_state),
        "fetched": _date_time(traffic_source.get("fetchedAt")),
    }
    devices = {
        "visitors": _number(devices_raw.get("visitors")),
        "total_visitors": _number(devices_raw.get("totalVisitors")),
        "partial": not bool(devices_raw.get("complete", True)),
        "chart": _device_chart(devices_raw),
        "badge": _badge(devices_state),
        "source_text": _source_text(devices_state),
        "fetched": _date_time(devices_source.get("fetchedAt")),
        "notice": None if devices_state == "ok" else {
            "stale": "数据源暂未更新，正在展示最近一次成功读取的记录。",
            "unconfigured": "设备分布尚未连接。",
        }.get(devices_state, "数据源暂不可用，稍后将自动重试。"),
        "available": bool(devices_raw.get("visitors")),
    }

    monitors = []
    uptime_ok = uptime_state == "ok"
    for item in uptime_raw.get("monitors") or []:
        monitor_state = _monitor_state(item, uptime_ok, now)
        history = item.get("history") or []
        monitor_current = item.get("current") or {}
        heartbeats = "".join(f'<span class="heartbeat-beat check-{point.get("status", "unknown")}"></span>' for point in history)
        monitors.append({
            "name": item.get("name") or "",
            "type": item.get("type") or "http",
            "state": monitor_state,
            "state_text": _monitor_text(monitor_state),
            "uptime": _percent(item.get("uptime24h")),
            "ping": "—" if monitor_current.get("ping") is None else f'{_number(monitor_current.get("ping"))} ms',
            "check_time": _short_date(monitor_current.get("time")),
            "history": history,
            "heartbeats": heartbeats,
            "history_start": _short_date(history[0].get("time")) if history else "—",
            "history_end": _short_date(history[-1].get("time")) if history else "—",
        })

    env = Environment(loader=FileSystemLoader(TEMPLATE_ROOT), autoescape=select_autoescape(["html", "xml"]))
    env.globals["icon"] = icon
    template = env.get_template("poster.html.j2")
    return template.render(
        styles=_styles(),
        background=f"data:{background_mime};base64,{base64.b64encode(background).decode('ascii')}",
        assets={
            "logo": _data_uri(STATUS_ROOT / "public" / "app_logo.png"),
            "uptime": _data_uri(STATUS_ROOT / "public" / "source-logos" / "uptime-kuma.svg"),
        },
        signal=_status_signal(result, now),
        sources=[
            src_item("server", "Komari", _data_uri(STATUS_ROOT / "public" / "source-logos" / "komari.png"), server_state),
            src_item("traffic", "Umami", _data_uri(STATUS_ROOT / "public" / "source-logos" / "umami.svg"), traffic_state),
            src_item("uptime", "Uptime Kuma", _data_uri(STATUS_ROOT / "public" / "source-logos" / "uptime-kuma.svg"), uptime_state),
        ],
        uptime_url=uptime_raw.get("statusPageUrl"),
        uptime_notice=None if uptime_state == "ok" else ("正在获取状态" if not uptime_source else {"stale": "数据源暂未更新，正在展示最近一次成功读取的记录。", "unconfigured": "配置数据源后将在此显示实时数据。"}.get(uptime_state, "数据源暂不可用，稍后将自动重试。")),
        monitors=monitors,
        uptime_badge=_badge(uptime_state),
        uptime_source_text={"ok": "已连接", "stale": "数据已过期", "unavailable": "暂时不可用", "unconfigured": "尚未连接"}.get(uptime_state, "暂时不可用"),
        uptime_fetched=_date_time(uptime_source.get("fetchedAt")),
        traffic=traffic,
        traffic_notice=None if traffic_state == "ok" else {"stale": "数据源暂未更新，正在展示最近一次成功读取的记录。", "unconfigured": "配置数据源后将在此显示实时数据。"}.get(traffic_state, "数据源暂不可用，稍后将自动重试。"),
        traffic_chart=_traffic_chart(traffic_raw),
        devices=devices,
        server={
            "name": server_name,
            "region": server.get("region") or "",
            "network_up": _bytes(current.get("networkUp")),
            "network_down": _bytes(current.get("networkDown")),
            "uptime": _duration(current.get("uptime"), True),
            "notice": None if server_state == "ok" else {"stale": "数据源暂未更新，正在展示最近一次成功读取的记录。", "unconfigured": "配置数据源后将在此显示实时数据。"}.get(server_state, "数据源暂不可用，稍后将自动重试。"),
            "history_stale": bool(server.get("historyStale")),
            "badge": _badge(server_state),
            "source_text": _source_text(server_state),
            "observed_at": _date_time(current.get("observedAt")),
            **server,
        },
        resources=resources,
        resource_chart=_resource_chart(server),
        year=datetime.now().year,
    )


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
