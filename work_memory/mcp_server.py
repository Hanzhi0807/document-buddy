from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Callable

from .toolkit import create_default_toolkit


JSONDict = dict[str, Any]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: JSONDict
    handler: Callable[[JSONDict], JSONDict]


class MCPServer:
    def __init__(self) -> None:
        self.toolkit = create_default_toolkit()
        self.tools = self._build_tools()

    def serve(self) -> None:
        while True:
            message = self._read_message()
            if message is None:
                break
            response = self._handle(message)
            if response is not None:
                self._write_message(response)

    def _build_tools(self) -> dict[str, ToolSpec]:
        def schema(properties: JSONDict, required: list[str]) -> JSONDict:
            return {"type": "object", "properties": properties, "required": required}

        common = {
            "workspace_id": {"type": "string", "description": "Workspace or Feishu tenant/chat id."},
            "project": {"type": "string", "description": "Project memory name."},
        }
        specs = [
            ToolSpec(
                "create_project_memory",
                "Create the standard wiki page set for a project memory.",
                schema(common, ["workspace_id", "project"]),
                lambda args: self.toolkit.create_project_memory(args["workspace_id"], args["project"]),
            ),
            ToolSpec(
                "get_project_index",
                "Return wiki page index and rules for a project memory.",
                schema(common, ["workspace_id", "project"]),
                lambda args: self.toolkit.get_project_index(args["workspace_id"], args["project"]),
            ),
            ToolSpec(
                "upsert_wiki_page",
                "Write or replace a wiki page. external_url may point to a Feishu Doc page.",
                schema(
                    {
                        **common,
                        "page_key": {"type": "string"},
                        "markdown": {"type": "string"},
                        "external_url": {"type": "string", "description": "Optional Feishu Doc URL for citations."},
                    },
                    ["workspace_id", "project", "page_key", "markdown"],
                ),
                lambda args: self.toolkit.upsert_wiki_page(
                    args["workspace_id"],
                    args["project"],
                    args["page_key"],
                    args["markdown"],
                    args.get("external_url", ""),
                ),
            ),
            ToolSpec(
                "list_project_memories",
                "List project memories in a workspace.",
                schema({"workspace_id": common["workspace_id"]}, ["workspace_id"]),
                lambda args: self.toolkit.list_project_memories(args["workspace_id"]),
            ),
            ToolSpec(
                "ingest_text",
                "Ingest text already retrieved from Feishu Docs, chat, files, or another client tool.",
                schema(
                    {
                        **common,
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "source_url": {"type": "string", "description": "Optional Feishu doc/message URL."},
                    },
                    ["workspace_id", "project", "title", "content"],
                ),
                lambda args: self.toolkit.ingest_text(
                    args["workspace_id"],
                    args["project"],
                    args["title"],
                    args["content"],
                    args.get("source_url", ""),
                ),
            ),
            ToolSpec(
                "list_wiki_pages",
                "List wiki pages for a project memory.",
                schema(common, ["workspace_id", "project"]),
                lambda args: self.toolkit.list_wiki_pages(args["workspace_id"], args["project"]),
            ),
            ToolSpec(
                "read_wiki_page",
                "Read one wiki page from a project memory.",
                schema({**common, "page_key": {"type": "string"}}, ["workspace_id", "project", "page_key"]),
                lambda args: self.toolkit.read_wiki_page(args["workspace_id"], args["project"], args["page_key"]),
            ),
            ToolSpec(
                "get_cited_context",
                "Return citation-bearing wiki context for a question. This tool does not invent answers.",
                schema({**common, "question": {"type": "string"}}, ["workspace_id", "project", "question"]),
                lambda args: self.toolkit.get_cited_context(args["workspace_id"], args["project"], args["question"]),
            ),
            ToolSpec(
                "query_project_wiki",
                "Alias of get_cited_context. Use it before answering any project question.",
                schema({**common, "question": {"type": "string"}}, ["workspace_id", "project", "question"]),
                lambda args: self.toolkit.query_project_wiki(args["workspace_id"], args["project"], args["question"]),
            ),
            ToolSpec(
                "lint_project_wiki",
                "Check missing pages, thin pages, and unresolved conflicts.",
                schema(common, ["workspace_id", "project"]),
                lambda args: self.toolkit.lint_project_wiki(args["workspace_id"], args["project"]),
            ),
            ToolSpec(
                "detect_conflicts",
                "List unresolved conflicts detected during ingestion.",
                schema(common, ["workspace_id", "project"]),
                lambda args: self.toolkit.detect_conflicts(args["workspace_id"], args["project"]),
            ),
        ]
        return {spec.name: spec for spec in specs}

    def _handle(self, message: JSONDict) -> JSONDict | None:
        method = message.get("method")
        msg_id = message.get("id")
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "gongzuo-wendang-dazi-mcp", "version": "0.1.0"},
                },
            }
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": spec.name,
                            "description": spec.description,
                            "inputSchema": spec.input_schema,
                        }
                        for spec in self.tools.values()
                    ]
                },
            }
        if method == "tools/call":
            params = message.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments") or {}
            spec = self.tools.get(name)
            if spec is None:
                return self._error(msg_id, -32601, f"Unknown tool: {name}")
            try:
                result = spec.handler(arguments)
            except Exception as exc:
                return self._error(msg_id, -32000, str(exc))
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, ensure_ascii=False, indent=2),
                        }
                    ]
                },
            }
        if msg_id is None:
            return None
        return self._error(msg_id, -32601, f"Unknown method: {method}")

    def _error(self, msg_id: Any, code: int, message: str) -> JSONDict:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    def _read_message(self) -> JSONDict | None:
        headers: dict[str, str] = {}
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                return None
            line = line.strip()
            if not line:
                break
            key, _, value = line.decode("ascii").partition(":")
            headers[key.lower()] = value.strip()
        length = int(headers.get("content-length", "0"))
        if length <= 0:
            return None
        body = sys.stdin.buffer.read(length)
        return json.loads(body.decode("utf-8"))

    def _write_message(self, message: JSONDict) -> None:
        body = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
        sys.stdout.buffer.write(body)
        sys.stdout.buffer.flush()


def main() -> None:
    MCPServer().serve()


if __name__ == "__main__":
    main()
