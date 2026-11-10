"""两个可单独测试的命令：extract 与 analyze。"""

import argparse
import os
import sys
from pathlib import Path

from autoboss.common.config import AIConfig
from autoboss.common.llm import JSONClient
from autoboss.resume.service import analyze_to_file, extract_to_files, load_source


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="autoboss", description="先提取 PDF 文字，再由 AI 分析成 JSON。")
    commands = parser.add_subparsers(dest="command", required=True)
    extract = commands.add_parser("extract", help="离线提取 PDF，输出 text.txt 和 source.json")
    extract.add_argument("pdf", type=Path, help="PDF 简历路径")
    extract.add_argument("--output-dir", type=Path, required=True, help="中间结果目录")
    extract.add_argument("--password-env", help="保存 PDF 密码的环境变量名称，不在命令行传密码")
    extract.add_argument("--force", action="store_true", help="覆盖已有提取结果")
    analyze = commands.add_parser("analyze", help="将 source.json 或 TXT 交给 AI，只输出 JSON")
    analyze.add_argument("source", type=Path, help="提取步骤的 source.json，或 UTF-8 TXT")
    analyze.add_argument("--output", type=Path, required=True, help="分析 JSON 的保存路径")
    analyze.add_argument("--env-file", type=Path, help="显式读取模型配置文件")
    analyze.add_argument("--model", help="覆盖 OPENAI_MODEL")
    analyze.add_argument("--base-url", help="覆盖 OPENAI_BASE_URL，包含 /v1 等完整基础路径")
    analyze.add_argument("--api-format", choices=["responses", "chat-completions"], help="模型接口协议")
    analyze.add_argument("--json-mode", action="store_true", help="接口不支持 JSON Schema 时改用 JSON 对象模式，仍进行本地校验")
    analyze.add_argument("--allow-partial", action="store_true", help="允许分析部分页面，明确标记缺页")
    analyze.add_argument("--force", action="store_true", help="覆盖已有分析结果")
    args = parser.parse_args(argv)
    try:
        if args.command == "extract":
            password = None
            if args.password_env:
                password = os.environ.get(args.password_env)
                if password is None:
                    raise ValueError("--password-env 指定的环境变量没有设置。")
            source = extract_to_files(args.pdf.expanduser(), args.output_dir.expanduser(), password=password, force=args.force)
            print(f"已提取 {source.page_count} 页、{len(source.blocks)} 个文字块。")
            print(f"文字：{(args.output_dir.expanduser() / 'text.txt').resolve()}")
            print(f"来源：{(args.output_dir.expanduser() / 'source.json').resolve()}")
            missing = [p.number for p in source.pages if p.status == "needs_ocr"]
            if missing:
                print(f"注意：第 {missing} 页需要 OCR。", file=sys.stderr)
        else:
            if args.source.expanduser().resolve() == args.output.expanduser().resolve():
                raise ValueError("输入与输出不能是同一个文件。")
            source = load_source(args.source.expanduser())
            config = AIConfig.load(env_file=args.env_file, model=args.model, base_url=args.base_url,
                                   api_format=args.api_format, json_mode=args.json_mode)
            result = analyze_to_file(source, args.output.expanduser(), JSONClient(config),
                                     force=args.force, allow_partial=args.allow_partial)
            print(f"JSON：{args.output.expanduser().resolve()}")
            print(f"工作 {len(result['employment'])} 段，项目 {len(result['projects'])} 个，其他 {len(result['other'])} 组。")
        return 0
    except (ValueError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
