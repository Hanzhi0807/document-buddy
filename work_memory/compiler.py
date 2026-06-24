from __future__ import annotations

import re
from dataclasses import dataclass

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


def _select_lines(text: str, keys: list[str], limit: int = 8) -> list[str]:
    sentences = split_sentences(text)
    hits: list[str] = []
    for sentence in sentences:
        lowered = sentence.lower()
        if any(key.lower() in lowered for key in keys):
            hits.append(sentence)
        if len(hits) >= limit:
            break
    return hits


def _bullet_list(items: list[str], empty: str) -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {compact_text(item, 240)}" for item in items)


def compile_project_memory(
    project_name: str,
    sources: list[dict[str, str]],
    existing_pages: dict[str, str],
) -> CompiledWiki:
    del existing_pages
    combined = "\n\n".join(source["text"] for source in sources)
    source_lines = "\n".join(
        f"- {source['title']} ({source['created_at']})" for source in sources[:30]
    )
    source_refs = "\n".join(f"- {source['title']}: {source['uri']}" for source in sources[:30])

    requirements = _select_lines(combined, KEYWORDS["requirements"])
    risks = _select_lines(combined, KEYWORDS["risks"])
    commitments = _select_lines(combined, KEYWORDS["commitments"])
    decisions = _select_lines(combined, KEYWORDS["decisions"])
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
    }
    summary = f"已更新 {len(pages)} 个项目记忆页面。"
    if conflicts:
        summary += f" 发现 {len(conflicts)} 个需要确认的问题。"
    return CompiledWiki(pages=pages, conflicts=conflicts, summary=summary)
