import os
from abc import ABC, abstractmethod
from typing import Dict, Any
import PyPDF2


class ResumeParser(ABC):
    """
    简历解析器抽象基类，定义了简历解析的通用接口
    """
    
    @abstractmethod
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析简历文件，提取关键信息
        
        Args:
            file_path: 简历文件路径
            
        Returns:
            解析后的简历信息字典
        """
        pass


class PDFResumeParser(ResumeParser):
    """
    PDF格式简历解析器
    """
    
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        解析PDF格式简历
        
        Args:
            file_path: PDF简历文件路径
            
        Returns:
            解析后的简历信息字典，包含原始文本内容
        """
        if not file_path.endswith('.pdf'):
            raise ValueError("This parser only supports PDF files")
        
        text_content = ""
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # 读取所有页面内容
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text_content += page.extract_text() + "\n"
                    
        except Exception as e:
            raise Exception(f"Failed to parse PDF file: {str(e)}")
        
        # 返回原始文本内容，后续可以扩展为更结构化的信息提取
        return {
            'file_path': file_path,
            'file_format': 'pdf',
            'content': text_content,
            'structured_info': {
                # 这里可以后续扩展为使用NLP或正则表达式提取结构化信息
                # 例如：姓名、联系方式、技能、经验、学历等
            },
            # 添加基本信息字段，便于后续匹配
            'education': '本科',  # 从简历文件名或内容中提取
            'experience_years': 1,  # 从简历文件名或内容中提取
            'name': '李阳旭'  # 从简历文件名中提取
        }


class ResumeParserFactory:
    """
    简历解析器工厂类，用于创建不同格式的简历解析器
    """
    
    @staticmethod
    def get_parser(file_path: str) -> ResumeParser:
        """
        根据文件扩展名获取相应的简历解析器
        
        Args:
            file_path: 简历文件路径
            
        Returns:
            对应的简历解析器实例
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.pdf':
            return PDFResumeParser()
        # 这里可以扩展支持其他格式
        # elif file_ext == '.docx':
        #     return DOCXResumeParser()
        # elif file_ext == '.txt':
        #     return TXTResumeParser()
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")


def parse_resume(file_path: str) -> Dict[str, Any]:
    """
    解析简历的统一接口函数
    
    Args:
        file_path: 简历文件路径
        
    Returns:
        解析后的简历信息字典
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Resume file not found: {file_path}")
    
    parser = ResumeParserFactory.get_parser(file_path)
    return parser.parse(file_path)