import os
import sys
from openai import OpenAI

# 强制设置标准输出和输入为 UTF-8 编码，解决 Windows 环境下的编码问题
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')


def chat_with_doubao():
    # --- 配置信息 ---
    # 建议将 API Key 设置在环境变量中，或者直接在这里填写
    # 替换为你的 API Key
    api_key = "0459f88a-a4a4-4ef4-ad16-9d21194ad22e" 
    
    # 替换为你的推理接入点 ID (Endpoint ID)，通常以 ep- 开头
    model_endpoint = "ep-20260406000532-kh9j2" 
    
    # 火山引擎 Ark 的基础 URL
    base_url = "https://ark.cn-beijing.volces.com/api/v3"

    # 初始化客户端
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    print("--- 已连接到豆包 API (输入 'exit' 或 'quit' 退出) ---")
    
    # 存储对话历史，让 AI 具有记忆
    messages = [
        {"role": "system", "content": "你是豆包，是由字节跳动开发的 AI 助手。"}
    ]

    while True:
        user_input = input("\n你: ")
        if user_input.lower() in ['exit', 'quit']:
            break
        
        # 将用户输入添加到对话历史
        messages.append({"role": "user", "content": user_input})

        try:
            # 发起流式请求
            stream = client.chat.completions.create(
                model=model_endpoint,
                messages=messages,
                stream=True
            )

            print("豆包: ", end="", flush=True)
            full_response = ""
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    print(content, end="", flush=True)
                    full_response += content

            print() # 换行
            
            # 将 AI 的回复添加到对话历史
            messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            print(f"\n[错误] 调用失败: {e}")

if __name__ == "__main__":
    chat_with_doubao()
