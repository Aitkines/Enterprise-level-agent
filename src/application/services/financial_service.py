import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.application.dto.financial_dto import FinancialTableDTO
from utils.financial_tools import get_company_fundamental

class FinancialService:
    def get_financial_table(self, symbol_raw: str) -> FinancialTableDTO | None:
        # 简单转换现有工具的返回值为 DTO
        import re
        symbol_match = re.search(r'\d{6}', str(symbol_raw))
        symbol = symbol_match.group(0) if symbol_match else "300750"
        
        try:
            data = get_company_fundamental(symbol)
            if data is not None:
                # 转换 list[dict] 或 DataFrame 为 DTO
                return FinancialTableDTO(data=data, source="东财/AkShare", unit_hint="元/比率")
            return None
        except Exception:
            return None
