import pdfplumber
import os

def extract_pdf_text_and_tables(pdf_path: str):
    """
    提取财务报告或行业研报中的文本和表格。
    """
    if not os.path.exists(pdf_path):
        return {"error": f"无法找到文件: {pdf_path}"}
    
    text = ""
    tables = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
                # 提取表格 (用于解析报表)
                tables.append(page.extract_table())
        
        return {
            "text": text,
            "tables": tables,
            "page_count": len(pdf.pages)
        }
    except Exception as e:
        return {"error": f"解析失败: {str(e)}"}

def summarize_key_points(text: str, max_len=1000):
    """
    简单的文本切片，供 AI 结合 RAG 应用于多模态场景。
    """
    # 如果文本过长，先截取关键部分或由 AI 进行全文摘要
    return text[:max_len] + "..." if len(text) > max_len else text

if __name__ == "__main__":
    # 测试
    # test_path = "智能体赋能的数据智能分析与决策支持应用系统.pdf"
    # print(extract_pdf_text_and_tables(test_path))
    pass
