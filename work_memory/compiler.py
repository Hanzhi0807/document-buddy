from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import quote

from .utils import compact_text, money_mentions, split_sentences, utc_now


@dataclass
class CompiledWiki:
    pages: dict[str, str]
    conflicts: list[tuple[str, str]]
    summary: str


KEYWORDS = {
    "requirements": ["需求", "需要", "希望", "要求", "目标", "关注", "偏好", "must", "need"],
    "risks": ["风险", "延期", "阻塞", "担心", "问题", "不确定", "法务", "预算", "risk", "issue"],
    "commitments": ["承诺", "跟进", "待办", "下周", "明天", "发送", "提供", "完成", "todo", "follow"],
    "decisions": ["决定", "确认", "同意", "选择", "定了", "通过", "decision", "approved"],
}


def _source_label(source: dict[str, str], line_no: int) -> str:
    title = source.get("title") or "未命名资料"
    uri = source.get("uri") or ""
    if uri:
        return f"{title} L{line_no}: {uri}"
    return f"{title} L{line_no}"


def _source_line_no(text: str, sentence: str) -> int:
    needle = sentence.strip()
    if not needle:
        return 1
    for line_no, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return line_no
    return 1


def _select_entries(sources: list[dict[str, str]], keys: list[str], limit: int = 8) -> list[str]:
    hits: list[str] = []
    for source in sources:
        text = source.get("text", "")
        sentences = split_sentences(text)
        for sentence in sentences:
            lowered = sentence.lower()
            if any(key.lower() in lowered for key in keys):
                line_no = _source_line_no(text, sentence)
                hits.append(f"{sentence} （来源：{_source_label(source, line_no)}）")
            if len(hits) >= limit:
                return hits
    return hits


def _bullet_list(items: list[str], empty: str) -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {compact_text(item, 240)}" for item in items)


def _page_link(page_key: str) -> str:
    return f"./{quote(page_key)}.md"


def _build_index(
    project_name: str,
    sources: list[dict[str, str]],
    conflicts: list[tuple[str, str]],
    now: str,
) -> str:
    latest_source = sources[0]["title"] if sources else "暂无资料"
    page_rows = [
        ("overview", "项目总览和最近理解"),
        ("requirements", "需求与关注点"),
        ("risks", "风险点"),
        ("commitments", "承诺与待办"),
        ("decisions", "决策记录"),
        ("people", "相关人物"),
        ("sources", "资料清单"),
        ("open-questions", "待确认问题"),
        ("log", "维护日志"),
    ]
    page_lines = "\n".join(f"- [{key}]({_page_link(key)})：{desc}" for key, desc in page_rows)
    return f"""# {project_name} Wiki Index

更新时间：{now}

## 回答规则

- 回答项目问题前必须先读取 wiki 证据。
- 只能使用带引用的 wiki 内容作答；wiki 没有证据时不要补编。
- 发现冲突时写入 open-questions，等待用户确认。

## 页面

{page_lines}

## 状态

- 已登记资料：{len(sources)} 份
- 最新资料：{latest_source}
- 待确认冲突：{len(conflicts)} 个
"""


def _build_log(
    project_name: str,
    sources: list[dict[str, str]],
    existing_pages: dict[str, str],
    conflicts: list[tuple[str, str]],
    now: str,
) -> str:
    previous_lines = [
        line
        for line in existing_pages.get("log", "").splitlines()
        if line.startswith("- ")
    ]
    new_line = f"- {now}：刷新 wiki，资料 {len(sources)} 份，待确认冲突 {len(conflicts)} 个。"
    log_lines = [new_line]
    for line in previous_lines:
        if line != new_line and line not in log_lines:
            log_lines.append(line)
        if len(log_lines) >= 20:
            break
    return f"""# {project_name} 维护日志

更新时间：{now}

{chr(10).join(log_lines)}
"""


def compile_project_memory(
    project_name: str,
    sources: list[dict[str, str]],
    existing_pages: dict[str, str],
) -> CompiledWiki:
    combined = "\n\n".join(source["text"] for source in sources)
    source_lines = "\n".join(
        f"- {source['title']} ({source['created_at']})：{source['uri']}" for source in sources[:30]
    )
    source_refs = "\n".join(f"- {source['title']}: {source['uri']}" for source in sources[:30])

    requirements = _select_entries(sources, KEYWORDS["requirements"])
    risks = _select_entries(sources, KEYWORDS["risks"])
    commitments = _select_entries(sources, KEYWORDS["commitments"])
    decisions = _select_entries(sources, KEYWORDS["decisions"])
    people = sorted(set(re.findall(r"@?[\u4e00-\u9fa5]{2,4}(?:经理|总|老师|同学|客户|法务|财务)?", combined)))
    people = [p for p in people if len(p) >= 2][:20]

    money = money_mentions(combined)
    conflicts: list[tuple[str, str]] = []
    if len(money) > 1:
        conflicts.append(
            (
                "budget-values",
                "发现多个金额/预算口径：" + "、".join(money[:8]) + "。需要用户确认以后哪个为准。",
            )
        )

    now = utc_now()
    overview_text = compact_text(combined, 1200) if combined else "暂无资料。"
    pages = {
        "index": _build_index(project_name, sources, conflicts, now),
        "overview": f"""# {project_name} 项目总览

更新时间：{now}

## 当前理解

{overview_text}

## 最近资料

{source_lines or "- 暂无资料"}
""",
        "requirements": f"""# {project_name} 需求与关注点

更新时间：{now}

{_bullet_list(requirements, "还没有明确提取到需求。")}
""",
        "risks": f"""# {project_name} 风险点

更新时间：{now}

{_bullet_list(risks, "还没有明确提取到风险。")}
""",
        "commitments": f"""# {project_name} 承诺与待办

更新时间：{now}

{_bullet_list(commitments, "还没有明确提取到承诺或待办。")}
""",
        "decisions": f"""# {project_name} 决策记录

更新时间：{now}

{_bullet_list(decisions, "还没有明确提取到决策。")}
""",
        "people": f"""# {project_name} 相关人物

更新时间：{now}

{_bullet_list(people, "还没有明确提取到人物。")}
""",
        "sources": f"""# {project_name} 资料清单

更新时间：{now}

{source_refs or "- 暂无资料"}
""",
        "open-questions": f"""# {project_name} 待确认问题

更新时间：{now}

{_bullet_list([description for _, description in conflicts], "暂时没有需要用户确认的问题。")}
""",
        "log": _build_log(project_name, sources, existing_pages, conflicts, now),
    }
    summary = f"已更新 {len(pages)} 个项目记忆页面。"
    if conflicts:
        summary += f" 发现 {len(conflicts)} 个需要确认的问题。"
    return CompiledWiki(pages=pages, conflicts=conflicts, summary=summary)
