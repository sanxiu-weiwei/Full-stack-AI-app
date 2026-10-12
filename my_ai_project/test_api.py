import os
from openai import OpenAI
from dotenv import load_dotenv
from db import save_message, load_messages

load_dotenv(override=True)

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://open.bigmodel.cn/api/paas/v4/"
)

SESSION_ID = "default_session"
history = load_messages(SESSION_ID)

if history:
    messages = [{"role": "system", "content": "你是一个乐于助人的编程助手。"}] + history
    print(f"📚 已从数据库恢复 {len(history)} 条历史消息")
else:
    messages = [{"role": "system", "content": "你是一个乐于助人的编程助手。"}]
    print("🆕 新会话，暂无历史记录")

print("🤖 终端聊天机器人已启动！(输入 'exit' 退出)")

while True:
    try:
        user_input = input("\n你: ")
        if user_input.lower() in ['exit', 'quit']:
            print("👋 再见！")
            break
        if not user_input.strip():
            continue

        save_message(SESSION_ID, "user", user_input)
        messages.append({"role": "user", "content": user_input})
        print("AI: ", end="", flush=True)

        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=messages,
            stream=True
        )

        ai_reply = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                piece = chunk.choices[0].delta.content
                ai_reply += piece
                print(piece, end="", flush=True)
        print()

        messages.append({"role": "assistant", "content": ai_reply})
        save_message(SESSION_ID, "assistant", ai_reply)

    except KeyboardInterrupt:
        print("\n👋 强制中断，再见！")
        break
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")