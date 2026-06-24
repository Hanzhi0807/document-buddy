from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any

from ..engine import WorkMemoryEngine


@dataclass(frozen=True)
class FeishuResponse:
    status: int
    body: dict[str, Any]


class FeishuAdapter:
    """Feishu/Lark webhook adapter.

    The adapter converts Feishu events into the two product actions:
    upload content and ask a question. File download and Feishu Docs writes are
    intentionally behind this adapter so the core engine stays platform-neutral.
    """

    def __init__(
        self,
        engine: WorkMemoryEngine,
        app_id: str = "",
        app_secret: str = "",
        verification_token: str = "",
        reply_enabled: bool = True,
    ) -> None:
        self.engine = engine
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self.reply_enabled = reply_enabled

    def handle_event(self, payload: dict[str, Any]) -> FeishuResponse:
        if "challenge" in payload:
            return FeishuResponse(200, {"challenge": payload["challenge"]})

        if self.verification_token and payload.get("token") not in {"", None, self.verification_token}:
            header = payload.get("header") or {}
            if header.get("token") != self.verification_token:
                return FeishuResponse(403, {"error": "invalid token"})

        event = payload.get("event") or {}
        event_type = (payload.get("header") or {}).get("event_type") or payload.get("type")
        if event_type and "message" not in event_type:
            return FeishuResponse(200, {"ok": True, "ignored": event_type})

        message = event.get("message") or {}
        chat_id = message.get("chat_id") or event.get("chat_id") or "feishu"
        message_id = message.get("message_id") or event.get("message_id")
        workspace_id = f"feishu-{chat_id}"
        project, action_text = self._parse_project_and_text(message)

        if not action_text:
            reply = "我是工作文档搭子。你可以发资料给我，也可以问我这个项目的问题。"
        elif self._looks_like_upload(action_text):
            result = self.engine.upload_content(
                workspace_id=workspace_id,
                project=project,
                title="飞书消息",
                content=action_text,
                filename="feishu-message.txt",
                source_type="feishu_message",
            )
            reply = result.message
            if result.conflicts:
                reply += "\n\n需要你确认：\n" + "\n".join(f"- {item}" for item in result.conflicts[:3])
        else:
            result = self.engine.ask(workspace_id=workspace_id, project=project, question=action_text)
            reply = result.answer

        if message_id and self.reply_enabled:
            self._reply_text(message_id, reply)
        return FeishuResponse(200, {"ok": True, "reply": reply})

    def _parse_project_and_text(self, message: dict[str, Any]) -> tuple[str, str]:
        message_type = message.get("message_type") or "text"
        raw_content = message.get("content") or ""
        content: dict[str, Any]
        if isinstance(raw_content, str):
            try:
                content = json.loads(raw_content)
            except json.JSONDecodeError:
                content = {"text": raw_content}
        else:
            content = raw_content

        if message_type == "text":
            text = str(content.get("text") or "").strip()
        elif message_type in {"file", "image", "media"}:
            name = content.get("file_name") or content.get("name") or "文件"
            token = content.get("file_key") or content.get("file_token") or content.get("image_key") or ""
            text = f"用户上传了{name}，平台文件标识：{token}。请在生产环境中通过飞书文件接口下载后整理。"
        else:
            text = json.dumps(content, ensure_ascii=False)

        project = "默认项目"
        for marker in ("项目：", "项目:", "#项目 "):
            if marker in text:
                before, after = text.split(marker, 1)
                first_line, _, rest = after.partition("\n")
                project = first_line.strip() or project
                text = (before + "\n" + rest).strip()
                break
        return project, text

    def _looks_like_upload(self, text: str) -> bool:
        upload_markers = ["整理进", "记录一下", "资料：", "资料:", "会议纪要", "聊天记录", "客户说", "补充信息"]
        question_markers = ["?", "？", "什么", "怎么", "为什么", "帮我", "总结", "准备", "写"]
        if any(marker in text for marker in upload_markers):
            return True
        if any(marker in text for marker in question_markers):
            return False
        return len(text) > 120

    def _tenant_access_token(self) -> str:
        if not self.app_id or not self.app_secret:
            return ""
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            data=json.dumps({"app_id": self.app_id, "app_secret": self.app_secret}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("tenant_access_token", "")

    def _reply_text(self, message_id: str, text: str) -> None:
        token = self._tenant_access_token()
        if not token:
            return
        body = {
            "msg_type": "text",
            "content": json.dumps({"text": text[:6000]}, ensure_ascii=False),
        }
        req = urllib.request.Request(
            f"https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10):
                return
        except OSError:
            if os.getenv("WORK_MEMORY_DEBUG"):
                raise
