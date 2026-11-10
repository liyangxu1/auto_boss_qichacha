"""从环境变量或显式配置文件读取模型配置，不打印密钥。"""

import os
import math
from dataclasses import dataclass, field
from pathlib import Path


def read_env_file(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    values = {}
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, separator, value = line.partition("=")
        if not separator or not key.strip().replace("_", "").isalnum():
            raise ValueError(f"配置文件第 {number} 行格式错误，应该为 KEY=VALUE。")
        value = value.strip()
        if value[:1] in {"'", '"'}:
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError(f"配置文件第 {number} 行引号未闭合。")
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].rstrip()
        values[key.strip()] = value
    return values


@dataclass(frozen=True)
class AIConfig:
    key: str = field(repr=False)
    model: str
    base_url: str
    api_format: str
    json_mode: bool = False
    timeout: float = 300
    direct: bool = False
    stream: bool = False
    enable_thinking: bool | None = None
    max_output_tokens: int | None = None
    temperature: float | None = None

    def __post_init__(self):
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("OPENAI_TIMEOUT 必须是大于 0 的有限秒数。")
        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("OPENAI_MAX_OUTPUT_TOKENS 必须是正整数。")
        if self.temperature is not None and (not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2):
            raise ValueError("OPENAI_TEMPERATURE 必须在0到2之间。")

    @classmethod
    def load(cls, *, env_file=None, model=None, base_url=None, api_format=None, json_mode=False):
        values = read_env_file(Path(env_file) if env_file else None)

        def value(key, default=""):
            return os.environ.get(key, values.get(key, default))

        try:
            timeout = float(value("OPENAI_TIMEOUT", "300"))
        except ValueError:
            raise ValueError("OPENAI_TIMEOUT 必须填写秒数，例如 300。") from None

        try:
            max_output_tokens = int(value("OPENAI_MAX_OUTPUT_TOKENS")) if value("OPENAI_MAX_OUTPUT_TOKENS") else None
            temperature = float(value("OPENAI_TEMPERATURE")) if value("OPENAI_TEMPERATURE") else None
        except ValueError:
            raise ValueError("模型最大输出长度或温度格式错误。") from None
        thinking = value("OPENAI_ENABLE_THINKING").lower()
        if thinking not in {"", "true", "false", "1", "0", "yes", "no"}:
            raise ValueError("OPENAI_ENABLE_THINKING 必须是true或false。")

        result = cls(key=value("OPENAI_API_KEY"), model=model or value("OPENAI_MODEL"),
                     base_url=base_url or value("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                     api_format=api_format or value("OPENAI_API_FORMAT", "responses"),
                     json_mode=json_mode or value("OPENAI_JSON_MODE", "false").lower() in {"true", "1", "yes"},
                     timeout=timeout, direct=value("OPENAI_DIRECT", "false").lower() in {"true", "1", "yes"},
                     stream=value("OPENAI_STREAM", "false").lower() in {"true", "1", "yes"},
                     enable_thinking=thinking in {"true", "1", "yes"} if thinking else None,
                     max_output_tokens=max_output_tokens, temperature=temperature)
        if not result.key or not result.model:
            raise ValueError("AI 分析需要 OPENAI_API_KEY 和 OPENAI_MODEL，请设置环境变量或使用 --env-file。")
        if result.api_format not in {"responses", "chat-completions"}:
            raise ValueError("OPENAI_API_FORMAT 只能为 responses 或 chat-completions。")
        return result
