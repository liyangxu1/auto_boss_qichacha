"""不覆盖已有测试结果；先暂存，再以原子替换写入文件。"""

import json
import os
import tempfile
from pathlib import Path


def write_files(files: dict[Path, str], *, force=False) -> None:
    files = {Path(path): text for path, text in files.items()}
    for path in files:
        if path.exists() and not force:
            raise ValueError(f"输出已存在：{path}；如需覆盖，请加 --force。")
        if path.exists() and not path.is_file():
            raise ValueError(f"输出路径不是普通文件：{path}")
    staged = {}
    installed = []
    backups = {p: p.read_bytes() if p.exists() else None for p in files}
    try:
        for path, text in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
                os.chmod(stream.name, 0o600)
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
                staged[path] = Path(stream.name)
        for path, temporary in staged.items():
            if force:
                os.replace(temporary, path)
            else:
                # 硬链接以独占方式创建目标，避免检查后另一个进程写入时被覆盖。
                os.link(temporary, path)
                temporary.unlink()
            installed.append(path)
    except Exception:
        for path in reversed(installed):
            if backups[path] is None:
                path.unlink(missing_ok=True)
            else:
                with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                    stream.write(backups[path])
                    temporary = Path(stream.name)
                os.replace(temporary, path)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def json_text(model) -> str:
    value = model.model_dump(mode="json") if hasattr(model, "model_dump") else model
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"
