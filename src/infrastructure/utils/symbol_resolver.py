import akshare as ak
import pandas as pd
import threading
import logging

logger = logging.getLogger(__name__)

class SymbolResolver:
    _instance = None
    _lock = threading.Lock()
    _mapping = {}  # name -> code
    _initialized = False

    # 常用 A 股股票代码静态兜底映射包
    _STATIC_FALLBACK = {
        "贵州茅台": "600519", "茅台": "600519",
        "宁德时代": "300750", "宁王": "300750",
        "平安银行": "000001", "平安": "000001",
        "招商银行": "600036", "招行": "600036",
        "中国平安": "601318",
        "比亚迪": "002594", "BYD": "002594",
        "隆基绿能": "601012", "隆基": "601012",
        "迈瑞医疗": "300760", "迈瑞": "300760",
        "海康威视": "002415", "海康": "002415",
        "亿纬锂能": "300014", "亿纬": "300014",
        "欣旺达": "300207",
        "国轩高科": "002074",
        "孚能科技": "688567",
        "鱼跃医疗": "002223",
        "乐普医疗": "300003",
        "泰格医药": "300347",
        "大华股份": "002236",
        "中科创达": "300496",
        "长江电力": "600900",
    }

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SymbolResolver, cls).__new__(cls)
        return cls._instance

    def _init_mapping(self):
        """初始化 A 股名称-代码映射表"""
        if self._initialized:
            return
        try:
            df = ak.stock_info_a_code_name()
            if not df.empty:
                # 建立双向映射或单向映射
                self._mapping = dict(zip(df['name'], df['code']))
                self._initialized = True
                logger.info(f"SymbolResolver initialized with {len(self._mapping)} stocks.")
        except Exception as e:
            logger.error(f"Failed to initialize SymbolResolver: {e}")

    def resolve(self, text: str) -> str:
        """
        解析文本中的公司名或代码。
        1. 如果本身是 6 位代码，直接返回。
        2. 如果是简称，从映射表中查询。
        """
        if not text:
            return text
        
        text = text.strip()
        
        # 如果已经是 6 位数字代码
        if text.isdigit() and len(text) == 6:
            return text
        
        # 兜底初始化
        if not self._initialized:
            self._init_mapping()
            
        # 优先级 1: 内存映射表 (akshare 实时抓取)
        if text in self._mapping:
            return self._mapping[text]
        
        # 优先级 2: 静态兜底表
        if text in self._STATIC_FALLBACK:
            return self._STATIC_FALLBACK[text]
        
        # 优先级 3: 模糊匹配 (内存表)
        for name, code in self._mapping.items():
            if text in name or name in text:
                return code
        
        # 优先级 4: 模糊匹配 (静态表)
        for name, code in self._STATIC_FALLBACK.items():
            if text in name or name in text:
                return code
                
        return text

resolver = SymbolResolver()
