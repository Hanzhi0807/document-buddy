from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from work_memory.toolkit import WorkMemoryToolkit

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


SOURCES = [
    {
        "file": "meeting-note.md",
        "title": "飞书会议纪要：A客户项目会前同步",
        "url": "https://feishu.example/doc/meeting-note-a-client",
    },
    {
        "file": "requirements.md",
        "title": "飞书需求文档：A客户项目需求摘要",
        "url": "https://feishu.example/doc/requirements-a-client",
    },
    {
        "file": "chat-excerpt.md",
        "title": "飞书群消息摘录：A客户项目跟进",
        "url": "https://feishu.example/message/chat-a-client-0624",
    },
]


def _print_json(title: str, payload: dict) -> None:
    print(f"\n## {title}")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def run_demo(data_dir: Path, keep_data: bool) -> int:
    source_dir = Path(__file__).resolve().parent / "offline_feishu_sources"
    toolkit = WorkMemoryToolkit(data_dir)
    workspace_id = "demo-tenant"
    project = "A客户项目"

    print("# 文档搭子离线飞书演示")
    print(f"data_dir: {data_dir}")

    for source in SOURCES:
        content = (source_dir / source["file"]).read_text(encoding="utf-8-sig")
        result = toolkit.ingest_text(
            workspace_id=workspace_id,
            project=project,
            title=source["title"],
            content=content,
            source_url=source["url"],
        )
        _print_json(f"ingest_text: {source['title']}", result)

    _print_json("list_wiki_pages", toolkit.list_wiki_pages(workspace_id, project))

    for question in ["明天和 A 客户开会前要注意什么？", "客户需要什么？"]:
        _print_json(
            f"query_project_wiki: {question}",
            toolkit.query_project_wiki(workspace_id, project, question),
        )

    _print_json("list_review_items", toolkit.list_review_items(workspace_id, project))

    if keep_data:
        wiki_dir = data_dir / workspace_id / "a客户项目" / "wiki"
        print(f"\n生成的 wiki 在：{wiki_dir}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the offline Document Buddy Feishu demo.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        help="Keep demo state in this directory instead of using a temporary directory.",
    )
    args = parser.parse_args()

    if args.data_dir:
        data_dir = args.data_dir.expanduser().resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        return run_demo(data_dir, keep_data=True)

    with tempfile.TemporaryDirectory() as tmp:
        return run_demo(Path(tmp), keep_data=False)


if __name__ == "__main__":
    raise SystemExit(main())
