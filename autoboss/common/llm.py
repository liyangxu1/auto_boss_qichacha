"""Responses 与 Chat Completions 的 JSON 输出适配，不安装额外 SDK。"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from .config import AIConfig


def strict_schema(model: type[BaseModel]) -> dict:
    schema = model.model_json_schema()

    def visit(node):
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(schema)
    return schema


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """避免凭证跟随意外重定向发送到其他地址。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class LLMError(ValueError):
    """只记录错误类型与字段位置，不把简历正文或密钥写入错误日志。"""

    def __init__(self, message, code, fields=None):
        super().__init__(message)
        self.code, self.fields = code, fields or []


class JSONClient:
    def __init__(self, config: AIConfig, transport: Callable | None = None):
        parsed = urllib.parse.urlsplit(config.base_url)
        if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("API 地址不合法，不能包含凭证、查询参数或片段。")
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
            raise ValueError("API 地址须使用 HTTPS，本机测试服务可使用 HTTP。")
        if config.api_format not in {"responses", "chat-completions"}:
            raise ValueError("不支持的 API 格式。")
        self.config, self.transport = config, transport
        suffix = "responses" if config.api_format == "responses" else "chat/completions"
        self.url = config.base_url.rstrip("/") + "/" + suffix

    def payload(self, text: str, model: type[BaseModel], instructions: str) -> dict:
        schema = strict_schema(model)
        description = {"type": "json_schema", "name": model.__name__, "strict": True, "schema": schema}
        if self.config.json_mode:
            description = {"type": "json_object"}
            instructions += "\n只输出 JSON，必须符合以下字段结构：" + json.dumps(schema, ensure_ascii=False)
        if self.config.api_format == "responses":
            return {"model": self.config.model, "store": False, "instructions": instructions,
                    "input": [{"role": "user", "content": [{"type": "input_text", "text": text}]}],
                    "text": {"format": description}}
        response_format = (description if self.config.json_mode else
                           {"type": "json_schema", "json_schema": {k: v for k, v in description.items() if k != "type"}})
        payload = {"model": self.config.model,
                "messages": [{"role": "system", "content": instructions}, {"role": "user", "content": text}],
                "response_format": response_format}
        if self.config.stream:
            payload["stream"] = True
        if self.config.enable_thinking is not None:
            payload["chat_template_kwargs"] = {"enable_thinking": self.config.enable_thinking}
        if self.config.max_output_tokens is not None:
            payload["max_tokens"] = self.config.max_output_tokens
        if self.config.temperature is not None:
            payload["temperature"] = self.config.temperature
        return payload

    def _read_stream(self, response, started):
        content, event = [], []
        finish, refusal, received = None, None, 0

        def consume():
            nonlocal finish, refusal
            if not event:
                return False
            raw = b"\n".join(event).strip()
            event.clear()
            if raw == b"[DONE]":
                return True
            value = json.loads(raw)
            if value.get("error"):
                raise LLMError("AI 流式接口返回错误，未保存结果。", "provider_error")
            for choice in value.get("choices", []):
                if choice.get("index", 0) != 0:
                    continue
                delta = choice.get("delta") or {}
                text = delta.get("content")
                if text is not None:
                    if not isinstance(text, str):
                        raise LLMError("AI 流式正文格式不正确。", "response_format")
                    content.append(text)
                refusal = delta.get("refusal") or refusal
                finish = choice.get("finish_reason") or finish
            return False

        for line in response:
            received += len(line)
            if received > 16 * 1024 * 1024:
                raise LLMError("模型响应过大，已停止读取。", "response_too_large")
            if time.monotonic() - started > self.config.timeout:
                raise TimeoutError()
            if not line.strip():
                if consume():
                    break
            elif line.startswith(b"data:"):
                event.append(line[5:].rstrip(b"\r\n"))
        else:
            consume()
        # 只有正文进入结构解析，思考过程不保存，也不拼入JSON。
        return {"choices": [{"finish_reason": finish, "message": {"content": "".join(content), "refusal": refusal}}]}

    def _request(self, payload: dict) -> dict:
        if self.transport:
            return self.transport(payload)
        request = urllib.request.Request(self.url, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.config.key})
        try:
            # 不自动重试，避免超时后产生重复请求；错误正文可能含个人信息，不回显。
            handlers = [NoRedirect()]
            if self.config.direct:
                handlers.insert(0, urllib.request.ProxyHandler({}))
            started = time.monotonic()
            with urllib.request.build_opener(*handlers).open(request, timeout=self.config.timeout) as result:
                if "text/event-stream" in result.headers.get("Content-Type", ""):
                    return self._read_stream(result, started)
                data = result.read(16 * 1024 * 1024 + 1)
                if len(data) > 16 * 1024 * 1024:
                    raise ValueError("模型响应过大，已停止读取。")
                return json.loads(data)
        except urllib.error.HTTPError as exc:
            raise LLMError(f"AI 接口返回 HTTP {exc.code}；请检查地址、模型权限及输出格式支持情况。", f"http_{exc.code}") from None
        except TimeoutError:
            raise LLMError(f"AI 接口等待响应超时（等待限制 {self.config.timeout:g} 秒）。"
                           "本次未生成分析结果；可在 .env 中调整 OPENAI_TIMEOUT 后手动重试。", "timeout") from None
        except json.JSONDecodeError as exc:
            raise LLMError("AI 接口未返回有效 JSON。", "invalid_json_response") from exc
        except OSError as exc:
            raise LLMError("AI 接口连接失败或对端断开。", "connection_error") from exc

    def extract(self, text: str, model: type[BaseModel], instructions: str):
        result = self._request(self.payload(text, model, instructions))
        try:
            if not isinstance(result, dict):
                raise ValueError("AI 接口未返回 JSON 对象。")
            if self.config.api_format == "responses":
                if result.get("status") != "completed":
                    raise ValueError("AI 响应未完整完成，未生成分析结果。")
                parts = [part for item in result.get("output", []) for part in item.get("content", [])]
                if any(part.get("type") == "refusal" for part in parts):
                    raise ValueError("AI 拒绝处理本次输入，未生成分析结果。")
                content = "".join(part["text"] for part in parts if part.get("type") == "output_text")
            else:
                choice = result["choices"][0]
                if choice.get("finish_reason") != "stop":
                    raise LLMError("AI 输出被截断或未正常结束，未生成分析结果。", "incomplete_output")
                if choice["message"].get("refusal"):
                    raise ValueError("AI 拒绝处理本次输入，未生成分析结果。")
                content = choice["message"]["content"]
            parsed = model.model_validate_json(content, strict=True)
            original = json.loads(content)

            def require_complete(raw, complete, pointer=""):
                # 本地模型默认值用于构造对象，但远端输出不得依赖默认值掩盖漏字段。
                if isinstance(complete, dict):
                    if not isinstance(raw, dict) or set(raw) != set(complete):
                        raise LLMError("AI 返回的 JSON 缺少必需字段或包含额外字段。", "schema_invalid",
                                       [{"path": pointer or "/", "type": "field_set_mismatch"}])
                    for key in complete:
                        require_complete(raw[key], complete[key], pointer + "/" + str(key))
                elif isinstance(complete, list):
                    for index, (a, b) in enumerate(zip(raw, complete)):
                        require_complete(a, b, pointer + "/" + str(index))

            require_complete(original, parsed.model_dump(mode="json"))
            return parsed
        except LLMError:
            raise
        except ValidationError as exc:
            fields = [{"path": "/" + "/".join(str(p)[:80] for p in e["loc"]), "type": e["type"]}
                      for e in exc.errors(include_input=False, include_context=False)[:20]]
            raise LLMError("AI 返回的 JSON 不符合要求的字段结构，未保存分析结果。", "schema_invalid", fields) from None
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ValueError("AI 响应结构与所选 API 格式不一致。") from exc
        except ValueError as exc:
            # 不把 Pydantic 的原始输入回显到命令行。
            if str(exc).startswith("AI "):
                raise
            raise ValueError("AI 返回的 JSON 不符合要求的字段结构，未保存分析结果。") from None
