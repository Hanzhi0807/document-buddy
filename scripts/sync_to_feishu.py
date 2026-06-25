from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from work_memory.toolkit import WorkMemoryToolkit  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


DEFAULT_WIKI_URL_TEMPLATE = "https://my.feishu.cn/wiki/{node_token}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync Document Buddy wiki pages to Feishu Wiki via lark-cli."
    )
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument(
        "--data-dir",
        default=os.environ.get("WORK_MEMORY_DATA_DIR", "data"),
        help="Document Buddy data directory. Defaults to WORK_MEMORY_DATA_DIR or ./data.",
    )
    parser.add_argument(
        "--root-node-token",
        help="Existing Feishu Wiki node used as the Document Buddy root.",
    )
    parser.add_argument(
        "--project-node-token",
        help="Existing Feishu Wiki project node. If set, pages are synced under this node.",
    )
    parser.add_argument(
        "--space-id",
        default="my_library",
        help="Target space for root creation when no root/project node token is provided.",
    )
    parser.add_argument("--root-title", default="文档搭子知识库")
    parser.add_argument(
        "--wiki-url-template",
        default=DEFAULT_WIKI_URL_TEMPLATE,
        help="Template used when node-list does not return URLs. Must contain {node_token}.",
    )
    parser.add_argument("--lark-cli", default="lark-cli")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the sync plan without calling Feishu.",
    )
    return parser.parse_args()


def lark_argv(lark_cli: str, args: Sequence[str]) -> list[str]:
    candidate = Path(lark_cli)
    if os.name == "nt" and candidate.suffix.lower() == ".ps1":
        return [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(candidate),
            *args,
        ]
    if os.name == "nt" and candidate.suffix == "":
        resolved = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "param($name) (Get-Command $name).Source",
                lark_cli,
            ],
            text=True,
            encoding="utf-8",
            capture_output=True,
            check=False,
        )
        source = resolved.stdout.strip()
        if resolved.returncode == 0 and source.lower().endswith(".ps1"):
            return [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                source,
                *args,
            ]
    return [lark_cli, *args]


def run_lark(lark_cli: str, args: Sequence[str]) -> dict[str, Any]:
    proc = subprocess.run(
        lark_argv(lark_cli, args),
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            "lark-cli failed: "
            + " ".join(args)
            + "\nSTDOUT:\n"
            + proc.stdout
            + "\nSTDERR:\n"
            + proc.stderr
        )
    start = proc.stdout.find("{")
    if start < 0:
        raise RuntimeError("lark-cli returned no JSON object:\n" + proc.stdout)
    return json.loads(proc.stdout[start:])


def wiki_url(template: str, node_token: str) -> str:
    return template.format(node_token=node_token)


def first_h1(markdown: str, fallback: str) -> str:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback


def list_children(lark_cli: str, space_id: str, parent_node_token: str) -> list[dict[str, Any]]:
    result = run_lark(
        lark_cli,
        [
            "wiki",
            "+node-list",
            "--as",
            "user",
            "--space-id",
            space_id,
            "--parent-node-token",
            parent_node_token,
            "--page-all",
            "--format",
            "json",
        ],
    )
    return list(result.get("data", {}).get("nodes", []))


def find_child(children: list[dict[str, Any]], candidates: set[str]) -> dict[str, Any] | None:
    for child in children:
        if str(child.get("title", "")) in candidates:
            return child
    return None


def create_node(
    lark_cli: str,
    title: str,
    *,
    parent_node_token: str | None = None,
    space_id: str | None = None,
) -> dict[str, Any]:
    args = ["wiki", "+node-create", "--as", "user", "--title", title, "--format", "json"]
    if parent_node_token:
        args.extend(["--parent-node-token", parent_node_token])
    elif space_id:
        args.extend(["--space-id", space_id])
    else:
        raise ValueError("parent_node_token or space_id is required")
    return dict(run_lark(lark_cli, args)["data"])


def update_doc_from_file(lark_cli: str, obj_token: str, markdown_path: Path) -> None:
    relative_path = markdown_path.relative_to(ROOT).as_posix()
    run_lark(
        lark_cli,
        [
            "docs",
            "+update",
            "--api-version",
            "v2",
            "--as",
            "user",
            "--doc",
            obj_token,
            "--command",
            "overwrite",
            "--doc-format",
            "markdown",
            "--content",
            "@" + relative_path,
            "--format",
            "json",
        ],
    )


def ensure_project_node(args: argparse.Namespace, project_body: str) -> dict[str, Any]:
    if args.project_node_token:
        return {
            "node_token": args.project_node_token,
            "url": wiki_url(args.wiki_url_template, args.project_node_token),
        }

    if args.root_node_token:
        root_node = {"node_token": args.root_node_token}
    else:
        root_node = create_node(args.lark_cli, args.root_title, space_id=args.space_id)

    root_token = str(root_node["node_token"])
    children = list_children(args.lark_cli, args.space_id, root_token)
    existing_project = find_child(children, {args.project})
    if existing_project:
        return existing_project

    project_node = create_node(args.lark_cli, args.project, parent_node_token=root_token)
    with tempfile.TemporaryDirectory(prefix=".tmp-document-buddy-sync-", dir=ROOT) as tmp:
        body_path = Path(tmp) / "project.md"
        body_path.write_text(project_body, encoding="utf-8")
        update_doc_from_file(args.lark_cli, str(project_node["obj_token"]), body_path)
    return project_node


def main() -> None:
    args = parse_args()
    toolkit = WorkMemoryToolkit(Path(args.data_dir))
    plan = toolkit.get_feishu_wiki_sync_plan(args.workspace_id, args.project, args.root_title)
    project_body = (
        f"# {args.project}\n\n"
        "This page holds the Document Buddy project wiki. Answers should use "
        "the cited pages below and avoid unsupported claims.\n"
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "target": plan["target"],
                    "page_count": len(plan["pages"]),
                    "pages": [
                        {
                            "page_key": page["page_key"],
                            "title": first_h1(page["markdown"], page["title"]),
                            "has_external_url": page["has_external_url"],
                        }
                        for page in plan["pages"]
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    project_node = ensure_project_node(args, project_body)
    project_token = str(project_node["node_token"])
    children = list_children(args.lark_cli, args.space_id, project_token)

    synced: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix=".tmp-document-buddy-sync-", dir=ROOT) as tmp:
        tmp_dir = Path(tmp)
        for page in plan["pages"]:
            page_key = str(page["page_key"])
            markdown = str(page["markdown"])
            feishu_title = first_h1(markdown, str(page["title"]))
            existing = find_child(children, {feishu_title, str(page["title"])})
            if existing:
                node = existing
                action = "updated"
            else:
                node = create_node(args.lark_cli, str(page["title"]), parent_node_token=project_token)
                children.append(node)
                action = "created"

            content_path = tmp_dir / f"{page_key}.md"
            content_path.write_text(markdown, encoding="utf-8")
            update_doc_from_file(args.lark_cli, str(node["obj_token"]), content_path)
            url = str(node.get("url") or wiki_url(args.wiki_url_template, str(node["node_token"])))
            toolkit.upsert_wiki_page(
                args.workspace_id,
                args.project,
                page_key,
                markdown,
                external_url=url,
            )
            synced.append(
                {"page_key": page_key, "title": feishu_title, "url": url, "action": action}
            )
            print(json.dumps(synced[-1], ensure_ascii=False), flush=True)

    print(json.dumps({"ok": True, "project_node": project_token, "pages": synced}, ensure_ascii=False))


if __name__ == "__main__":
    main()
