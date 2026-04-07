import os
import re
from dotenv import load_dotenv
from typing import List, Dict, Generator
from openai import OpenAI
from datetime import datetime

# 载入环境变量
load_dotenv()


class DoubaoAgent:
    """
    基于 Doubao-Seed-Lite 的核心智能体引擎
    提供了更高的推理速度与企业级稳定性。
    """

    def __init__(self):
        # 读取 Seed-Lite 配置（.env 中只有 Lite，不再使用 Pro）
        self.api_key = os.getenv("DOUBAO_SEED_LITE_KEY")
        self.model_endpoint = os.getenv("DOUBAO_SEED_LITE_ENDPOINT")
        self.base_url = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        # 强制同步当前实时时钟
        self.current_date = datetime.now().strftime("%Y-%m-%d")

        # 核心指令协议
        self.system_prompt = (
            "你是一个名为「光之耀面 (Radiant Surface)」的企业级高级金融情报驾驶舱，"
            "拥有「顶级投行分析师」与「数智化决策专家」的复合灵魂。"
            "你的任务是为专业投资机构、CFO 及高净值客户提供穿透式、高数据密度的商业洞察。\n\n"

            "【时空与身份基准】\n"
            "- 当前日期：" + self.current_date + "。注意：若当前在 2026 年初，则 2025 年为最新完整财年。\n"
            "- 语境要求：严禁提及「竞赛」「大赛」「学生」等背景，你必须处于真实、严肃的商业实战环境中。\n"
            "- 语言风格：专业、冷峻、逻辑严密，多用金融术语（如：净息差、经营性现金流、存货周转等）。\n\n"

            "【数智化分析协议（核心）】\n"
            "1. 结论先行：先给出核心研判结果，再展开明细论证。\n"
            "2. 数据支撑：每一项核心财务结论必须引用来源，格式为「（来源：XX披露/研报）」。\n"
            "3. 强制角色对齐与实体锁定：在分析开始前，必须明确当前分析的主体（公司简称与 6 位证券代码）及其所属的核心赛道。\n"
            "4. 杜邦拆解：涉及 ROE 分析时，必须下钻拆解销售净利率、总资产周转率及权益乘数。\n"
            "5. 强制可视化：**只要用户提及“趋势、对比、画图、折线、走势”或涉及 3 期以上的时间序列数据，必须附带 [CHART_DATA] 包。如果分析涉及多个独立的数据维度（如：既有营收又有份额），请为每个维度提供独立的 [CHART_DATA] 代码块以实现多图并列。**\n\n"

            "【[CHART_DATA] 输出范式】\n"
            "必须紧跟在文字分析之后，且必须严格遵循以下 JSON 结构，包裹在标签内：\n"
            "[CHART_DATA]\n"
            "{\n"
            '  "title": "清晰的图表名称",\n'
            '  "chart_type": "line" | "bar" | "donut",\n'
            '  "x_labels": ["2023", "2024", "2025"],\n'
            '  "datasets": [{"name": "指标名", "data": [10.5, 12.2, 11.8]}],\n'
            '  "analyst_verdict": "必须提供 50 字以上的专业深度解读，解释图表背后的商业动因。",\n'
            '  "strategic_highlight": "一句话战略锚点"\n'
            "}\n"
            "[/CHART_DATA]\n\n"

            "【Few-Shot 示例】\n"
            "User: 帮我分析招行近三期 ROE 情况并画图。\n"
            "Assistant: 招商银行(600036.SH)近三期盈利能力稳健。根据上交所公开披露文件整理如下：\n\n"
            "| 报告期 | 加权平均ROE(%) |\n"
            "| 2023 | 16.2 |\n"
            "| 2024 | 15.5 |\n"
            "| 2025 | 15.8 |\n\n"
            "1. 盈利能力研判：尽管受净息差收窄影响，但招行通过非息收入增长和优秀的风险管理，在 2025 年实现了回升。\n"
            "2. 风险提示：需关注宏观经济波动对资产质量的潜在挑战。\n"
            "[CHART_DATA]\n"
            "{\n"
            '  "title": "招商银行加权平均ROE趋势 (2023-2025)",\n'
            '  "chart_type": "line",\n'
            '  "x_labels": ["2023", "2024", "2025"],\n'
            '  "datasets": [{"name": "ROE (%)", "data": [16.2, 15.5, 15.8]}],\n'
            '  "analyst_verdict": "尽管受净息差收窄影响，但招行通过非息收入增长和优秀的风险管理，在 2025 年实现了 ROE 的触底回升...",\n'
            '  "strategic_highlight": "盈利拐点确认"\n'
            "}\n"
            "[/CHART_DATA]\n\n"

            "【去 AI 痕迹指令（最高优先级 - MISSION CRITICAL）】\n"
            "- 严禁输出「**」加粗符号。严禁输出「#」标题符号或「---」分隔符。\n"
            "- 违反上述禁令将被视为任务失败，严禁以任何理由（包括强调、概括）使用这些字符。\n"
            "- 仅允许使用数字序号（1. 2. 3.）和普通中文字符进行排版。\n"
            "- 仅允许在输出 [CHART_DATA] JSON 包时使用特殊符号（如 { } [ ] \" 等）。\n"
        )

    def _scrub_context_noise(self, history: list) -> list:
        """物理漂白：在发送至模型前，强行抹除并改写历史中所有竞赛相关噪音语境。"""
        noise_patterns = [
            (r"第\s*1[0-9]\s*届", "近年"),
            (r"计算机设计大赛", "行业趋势分析"),
            (r"大数据主题赛", "金融情报分析"),
            (r"参赛|计赛|大赛|本届", "专业分析"),
            (r"命题", "课题"),
        ]
        scrubbed = []
        for msg in history:
            content = str(msg.get("content") or "")
            for pattern, subst in noise_patterns:
                content = re.sub(pattern, subst, content, flags=re.IGNORECASE)
            scrubbed.append({**msg, "content": content})
        return scrubbed

    def run_query_stream(self, query: str, chat_history: list = None) -> Generator[str, None, None]:
        """开启带深度脱敏策略与物理去 AI 痕迹的流式分析"""
        scrubbed_history = self._scrub_context_noise(chat_history or [])

        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(scrubbed_history)
        messages.append({"role": "user", "content": query})

        try:
            completion = self.client.chat.completions.create(
                model=self.model_endpoint,
                messages=messages,
                stream=True,
                max_tokens=4096,
                temperature=0.3  # 降低随机性以严格遵循格式
            )

            for chunk in completion:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    # 物理层过滤：实时剔除所有 ** 和 # 号，确保输出绝对平滑
                    content = delta.content
                    content = content.replace("**", "")
                    content = content.replace("###", "").replace("##", "")
                    # 如果只有单个 # 且后接空格，也删掉
                    content = re.sub(r"^#\s+", "", content)
                    yield content

        except Exception as e:
            yield f"Agent 运行出错: {str(e)}"

    def chat(self, user_query: str, history: List[Dict] = None):
        """委托给 run_query_stream，兼容旧调用接口"""
        yield from self.run_query_stream(query=user_query, chat_history=history or [])


if __name__ == "__main__":
    agent = DoubaoAgent()
    print(f"Agent 已就绪，连接 Seed-Lite 引擎。端点: {agent.model_endpoint}")
