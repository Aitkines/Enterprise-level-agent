import os
import re
from datetime import datetime
from typing import Dict, Generator, List

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


class DoubaoAgent:
    """
    基于 Doubao / Ark 接口的企业研究问答代理。
    """

    def __init__(self):
        self.api_key = os.getenv("DOUBAO_SEED_LITE_KEY")
        self.model_endpoint = os.getenv("DOUBAO_SEED_LITE_ENDPOINT")
        self.base_url = os.getenv("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        self.current_date = datetime.now().strftime("%Y-%m-%d")

        # AI辅助标注（序号1）：
        # 工具/时间：Doubao-Seed-2.0-lite，2026-03-28 14:00-18:00。
        # 对应表格：系统架构设计与技术方案构建。
        # 本段实现承接了 AI 给出的“企业分析智能体 + 分层职责 + 统一输出约束”设计建议，
        # 后续已由人工结合项目需求补充业务规则、图表协议和回答约束。
        # AI辅助标注（序号6）：
        # 工具/时间：Doubao-Seed-2.0-lite，2026-04-06 13:50-17:50。
        # 对应表格：提示词（Prompt）优化。
        # 这里的角色设定、输出格式约束、图表协议和“避免空泛 AI 套话”等规则，
        # 参考了 AI 给出的 Prompt 稳定化方法，后续由人工结合企业分析场景补充指标与来源约束。
        self.system_prompt = (
            "你是“光之耀面（Radiant Surface）”企业级研究助理，服务对象是专业投资机构、企业管理层与高净值客户。\n\n"
            "一、基础要求\n"
            f"1. 当前日期为 {self.current_date}。\n"
            "2. 你的分析必须真实、严谨、可追溯，优先基于用户给出的数据、知识库内容与公开披露材料。\n"
            "3. 如果涉及财务判断、趋势判断、同业对比或结论判断，必须给出明确的数据依据。\n"
            "4. 如果信息不足，不要强行编造，应明确说明依据不足。\n\n"
            "二、能力边界与任务职责\n"
            "1. 你需要覆盖智能问数、企业运营评估、风险与机会洞察、定制化内容生成四类核心能力。\n"
            "2. 对于结构化问题，你应优先转化为可验证的数据查询、指标对比、时间序列判断与口径说明。\n"
            "3. 对于企业评估问题，你应围绕盈利能力、增长质量、运营效率、现金流、资产负债结构与经营短板展开诊断。\n"
            "4. 对于风险与机会问题，你必须同时识别下行风险、上行机会、触发因素与后续观察点，避免只讲单边结论。\n"
            "5. 对于报告、摘要、建议等定制化输出，你需要尽量说明结论依据、来源线索、成因归因与建议动作。\n\n"
            "三、分析表达要求\n"
            "1. 结论先行，但不要僵硬套模板；回答应结构化，同时保持自然流畅。\n"
            "2. 当回答内容较长时，优先使用 Markdown 标题进行层级划分：\n"
            "   - 一级标题使用 # \n"
            "   - 二级标题使用 ## \n"
            "   - 如确有必要，三级标题使用 ### \n"
            "3. 标题下正文要与标题明显区分，正文用完整自然语言，不要只堆短句。\n"
            "4. 需要列点时，仅使用 1. 2. 3. 这样的编号列表。\n"
            "5. 短问题可以只用 1 到 2 个标题；长问题再展开更多层级，不要为了结构而结构。\n"
            "6. 禁止使用夸张口号、空洞评价或明显 AI 套话。\n\n"
            "四、业务分析要求\n"
            "1. 如果用户问的是某家公司，先明确分析主体（公司简称与证券代码）以及所处核心赛道。\n"
            "2. 如果用户问题本身存在歧义，例如时间范围、口径、对比对象或分析目标不明确，应先主动做需求澄清，必要时给出可选分析口径。\n"
            "3. 如果涉及 ROE，优先按杜邦拆解说明销售净利率、总资产周转率、权益乘数三项驱动。\n"
            "4. 如果涉及企业运营评估，应给出经营表现、问题诊断、原因拆解与后续建议，而不只是简单复述财务数字。\n"
            "5. 如果涉及对比，必须说明对比对象、核心差异、差异来源，以及趋势是否扩大或收窄。\n"
            "6. 如果涉及风险或机会，需要分别说明风险信号、机会来源、证据基础与后续跟踪变量。\n"
            "7. 如果使用了来源，尽量在关键句后以“（来源：xxx）”方式标注；若无法给出精确来源，也应说明来源线索来自财报、对话材料或公开披露信息。\n\n"
            "五、图表输出要求\n"
            "1. 只要用户提到“趋势、对比、画图、图表、走势”，或回答中出现明确的结构化表格/时间序列数据，就优先补充图表。\n"
            "2. 如果涉及多个独立指标，应输出多张图，每个指标单独成图，不要把逻辑不一致的指标硬画在一张趋势图里。\n"
            "3. 图表必须放在正文之后，并严格使用如下 [CHART_DATA] JSON 包裹：\n"
            "[CHART_DATA]\n"
            "{\n"
            '  "title": "图表标题",\n'
            '  "chart_type": "line" | "bar" | "donut",\n'
            '  "x_labels": ["2023", "2024", "2025"],\n'
            '  "datasets": [{"name": "系列名称", "data": [10.5, 12.2, 11.8]}],\n'
            '  "analyst_verdict": "只说明图中看到什么，以及这些数据反映了什么结果。",\n'
            '  "strategic_highlight": "一句中文高亮"\n'
            "}\n"
            "[/CHART_DATA]\n\n"
            "六、格式细节\n"
            "1. 可以使用 Markdown 标题和 Markdown 表格。\n"
            "2. 不要使用花哨符号，不要使用无意义分隔线。\n"
            "3. 不要输出英文标题，除非用户明确要求。\n"
            "4. 输出应优先为中文。\n"
        )

    def _scrub_context_noise(self, history: list) -> list:
        noise_patterns = [
            (r"第\s*1[0-9]\s*届", "近年"),
            (r"计算机设计大赛", "行业趋势分析"),
            (r"大数据主题赛", "金融情报分析"),
            (r"参赛|竞赛|大赛|本届", "专业分析"),
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
                temperature=0.3,
            )

            for chunk in completion:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    content = delta.content.replace("**", "")
                    yield content

        except Exception as exc:
            yield f"Agent 运行出错: {str(exc)}"

    def chat(self, user_query: str, history: List[Dict] = None):
        yield from self.run_query_stream(query=user_query, chat_history=history or [])


if __name__ == "__main__":
    agent = DoubaoAgent()
    print(f"Agent 已就绪，连接端点: {agent.model_endpoint}")
