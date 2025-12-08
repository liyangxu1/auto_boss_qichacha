#!/usr/bin/env python3
"""
测试简历解析功能的脚本
"""

import os
import sys

# 添加项目根目录到搜索路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.resume_parser import parse_resume


def main():
    """
    主函数，测试简历解析功能
    """
    # 获取命令行参数
    if len(sys.argv) != 2:
        print("Usage: python test_resume_parser.py <resume_file_path>")
        print("Example: python test_resume_parser.py data/jianli/resume.pdf")
        return
    
    resume_path = sys.argv[1]
    
    try:
        # 解析简历
        print(f"正在解析简历: {resume_path}")
        result = parse_resume(resume_path)
        
        # 打印解析结果
        print("\n解析结果:")
        print(f"文件路径: {result['file_path']}")
        print(f"文件格式: {result['file_format']}")
        
        # 打印前500个字符的内容
        content_preview = result['content'][:500]
        if len(result['content']) > 500:
            content_preview += "..."
        
        print(f"\n简历内容预览:\n{content_preview}")
        
        print("\n简历解析成功!")
        
    except Exception as e:
        print(f"\n简历解析失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()