from __future__ import annotations

import base64
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .adapters.feishu import FeishuAdapter
from .config import load_settings
from .db import Database
from .engine import WorkMemoryEngine
from .storage import FeishuDocsStorageProvider, LocalStorageProvider


INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>工作文档搭子</title>
  <style>
    :root { color-scheme: light; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1f2328; }
    main { max-width: 920px; margin: 0 auto; padding: 32px 18px 56px; }
    header { margin-bottom: 24px; }
    h1 { font-size: 30px; margin: 0 0 8px; }
    p { line-height: 1.65; }
    section { background: #fff; border: 1px solid #d8dee4; border-radius: 8px; padding: 18px; margin: 14px 0; }
    label { display: block; font-weight: 650; margin: 10px 0 6px; }
    input, textarea { width: 100%; box-sizing: border-box; border: 1px solid #c9d1d9; border-radius: 6px; padding: 10px 12px; font: inherit; }
    textarea { min-height: 130px; resize: vertical; }
    button { margin-top: 12px; border: 0; border-radius: 6px; background: #0969da; color: #fff; padding: 10px 14px; font-weight: 650; cursor: pointer; }
    button.secondary { background: #57606a; }
    pre { white-space: pre-wrap; background: #f6f8fa; border-radius: 6px; padding: 12px; min-height: 80px; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
    @media (max-width: 760px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>工作文档搭子</h1>
      <p>这个本地页面只是功能验证。正式使用时，它应该住在飞书、钉钉或企业微信里：发资料给它，它记住；问它问题，它回答。</p>
    </header>
    <div class="grid">
      <section>
        <h2>上传内容</h2>
        <label>项目名</label>
        <input id="uploadProject" value="A客户项目" />
        <label>标题</label>
        <input id="title" value="会议纪要" />
        <label>资料内容</label>
        <textarea id="content">项目：A客户项目
昨天会议纪要：客户希望 7 月完成试点，预算口径提到 80 万。法务担心数据权限，需要我们下周提供实施排期。</textarea>
        <button onclick="uploadText()">整理进去</button>
      </section>
      <section>
        <h2>问问题</h2>
        <label>项目名</label>
        <input id="askProject" value="A客户项目" />
        <label>问题</label>
        <textarea id="question">明天和 A 客户开会前我该注意什么？</textarea>
        <button onclick="ask()">问工作文档搭子</button>
      </section>
    </div>
    <section>
      <h2>结果</h2>
      <pre id="result">等待操作...</pre>
    </section>
  </main>
  <script>
    async function postJson(url, body) {
      const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      const data = await res.json();
      document.getElementById("result").textContent = data.answer || data.message || JSON.stringify(data, null, 2);
    }
    function uploadText() {
      postJson("/api/upload", {
        workspace_id: "local-demo",
        project: document.getElementById("uploadProject").value,
        title: document.getElementById("title").value,
        content: document.getElementById("content").value
      });
    }
    function ask() {
      postJson("/api/ask", {
        workspace_id: "local-demo",
        project: document.getElementById("askProject").value,
        question: document.getElementById("question").value
      });
    }
  </script>
</body>
</html>"""


class App:
    def __init__(self) -> None:
        self.settings = load_settings()
        db = Database(self.settings.data_dir / "state.sqlite")
        if self.settings.storage_provider == "feishu_docs":
            storage = FeishuDocsStorageProvider(
                self.settings.data_dir / "cache",
                docs_space_token=self.settings.feishu_docs_space_token,
            )
        else:
            storage = LocalStorageProvider(self.settings.data_dir)
        self.engine = WorkMemoryEngine(db=db, storage=storage)
        self.feishu = FeishuAdapter(
            engine=self.engine,
            app_id=self.settings.feishu_app_id,
            app_secret=self.settings.feishu_app_secret,
            verification_token=self.settings.feishu_verification_token,
            reply_enabled=self.settings.feishu_reply_enabled,
        )


APP = App()


class Handler(BaseHTTPRequestHandler):
    server_version = "WendangDazi/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_html(INDEX_HTML)
        elif path == "/health":
            self._send_json({"ok": True, "name": "工作文档搭子"})
        elif path == "/api/projects":
            query = parse_qs(urlparse(self.path).query)
            workspace_id = query.get("workspace_id", ["local-demo"])[0]
            self._send_json({"projects": APP.engine.list_projects(workspace_id)})
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._read_json()
            if path == "/api/upload":
                result = APP.engine.upload_content(
                    workspace_id=body.get("workspace_id", "local-demo"),
                    project=body.get("project", "默认项目"),
                    title=body.get("title", "资料"),
                    content=body.get("content", ""),
                    filename=body.get("filename", "note.txt"),
                )
                self._send_json(
                    {
                        "project_id": result.project_id,
                        "source_id": result.source_id,
                        "message": result.message,
                        "conflicts": result.conflicts,
                    }
                )
            elif path == "/api/upload-file":
                result = APP.engine.upload_file_base64(
                    workspace_id=body.get("workspace_id", "local-demo"),
                    project=body.get("project", "默认项目"),
                    title=body.get("title", body.get("filename", "文件")),
                    filename=body.get("filename", "upload.txt"),
                    data_base64=body.get("data_base64", base64.b64encode(b"").decode()),
                )
                self._send_json({"message": result.message, "conflicts": result.conflicts})
            elif path == "/api/ask":
                result = APP.engine.ask(
                    workspace_id=body.get("workspace_id", "local-demo"),
                    project=body.get("project", "默认项目"),
                    question=body.get("question", ""),
                )
                self._send_json(
                    {"project_id": result.project_id, "answer": result.answer, "sources": result.sources}
                )
            elif path == "/webhook/feishu":
                result = APP.feishu.handle_event(body)
                self._send_json(result.body, status=result.status)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        if not raw:
            return {}
        return json.loads(raw.decode("utf-8"))

    def _send_json(self, data: dict, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_html(self, html: str) -> None:
        raw = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> None:
    settings = APP.settings
    server = ThreadingHTTPServer((settings.host, settings.port), Handler)
    print(f"工作文档搭子正在运行：http://{settings.host}:{settings.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
