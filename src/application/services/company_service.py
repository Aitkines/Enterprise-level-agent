import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.infrastructure.utils.file_processor import FileProcessor
from src.infrastructure.utils.symbol_resolver import resolver
from utils.financial_tools import get_company_fundamental

class CompanyService:
    def identify_target_companies(self, prompt):
        """核心实体识别：提取 prompt 中的公司名或股票代码"""
        from agent_engine import DoubaoAgent
        agent = DoubaoAgent()
        ner_prompt = f"""
        请从以下文本中提取出所有提到或隐含的上市公司。
        对于每个公司，请输出其 6 位证券代码（如 600519）。如果你不确定代码，请输出公司简称。
        用英文逗号分隔多个结果。如果没有找到任何公司，则输出 'NONE'。
        示例输入：'帮我分析一下茅台和腾讯'
        示例输出：'600519, 腾讯'
        
        待分析文本：
        {prompt}
        """
        try:
            # 这是一个极小延迟的同步调用
            response = agent.client.chat.completions.create(
                model=agent.model_endpoint,
                messages=[{"role": "user", "content": ner_prompt}],
                temperature=0
            )
            raw = response.choices[0].message.content
            if 'NONE' in raw:
                return []
            
            extracted = [x.strip() for x in raw.replace('[', '').replace(']', '').split(',') if x.strip()]
            
            # 使用 SymbolResolver 强化锁定：尝试将名称映射为代码
            resolved = []
            for item in extracted:
                code = resolver.resolve(item)
                if code and code not in resolved:
                    resolved.append(code)
            return resolved
        except:
            return []

    def parse_company_choice(self, target):
        """返回 (标的代码, 标的展示名称)"""
        code = resolver.resolve(target)
        # 这里实际上可以更进一步，反向查找名称
        return code, target

    def get_financial_data(self, symbol):
        # 确保 symbol 是代码
        code = resolver.resolve(symbol)
        return get_company_fundamental(code)
