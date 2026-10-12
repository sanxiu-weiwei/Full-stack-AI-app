import os
import datetime
import requests
import json
from dotenv import load_dotenv
from db import get_plugins
from llm_factory import get_client, get_image_model

load_dotenv(override=True)


# ==================== 内置工具实现 ====================
def get_current_time():
    now = datetime.datetime.now()
    return {"当前时间": now.strftime("%Y年%m月%d日 %H:%M:%S"),
            "星期": ["一", "二", "三", "四", "五", "六", "日"][now.weekday()]}


def get_weather(city: str):
    try:
        res = requests.get(f"https://wttr.in/{city}?format=j1", timeout=8)
        data = res.json()
        cur = data["current_condition"][0]
        return {"城市": city, "温度": f"{cur['temp_C']}°C",
                "天气": cur["weatherDesc"][0]["value"], "湿度": f"{cur['humidity']}%"}
    except Exception as e:
        return {"error": f"天气查询失败: {str(e)}"}


def calculate(expression: str):
    try:
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expression):
            return {"error": "只允许数字和 +-*/(). 运算符"}
        result = eval(expression, {"__builtins__": {}}, {})
        return {"表达式": expression, "结果": result}
    except Exception as e:
        return {"error": f"计算失败: {str(e)}"}


def generate_image(prompt: str, user_id: int):
    """根据当前用户配置的画图模型生成图片"""
    image_model = get_image_model(user_id)
    if not image_model:
        return {"error": "当前模型配置不支持画图，请到⚙️设置里更换支持画图的配置"}
    try:
        client = get_client(user_id)
        response = client.images.generate(
            model=image_model,
            prompt=prompt,
            size="1024x1024"
        )
        return {"image_url": response.data[0].url, "prompt": prompt}
    except Exception as e:
        return {"error": f"图片生成失败: {str(e)}"}


# ==================== 工具定义 ====================
BUILTIN_TOOLS = [
    {
        "type": "function",
        "function": {"name": "get_current_time", "description": "获取当前的日期、时间和星期几。",
                     "parameters": {"type": "object", "properties": {}}},
        "meta": {"icon": "🕒", "label": "获取当前时间"}
    },
    {
        "type": "function",
        "function": {"name": "get_weather", "description": "查询指定城市的实时天气。",
                     "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}},
        "meta": {"icon": "🌤️", "label": "查询实时天气"}
    },
    {
        "type": "function",
        "function": {"name": "calculate", "description": "计算数学表达式。",
                     "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}},
        "meta": {"icon": "🔢", "label": "数学计算器"}
    },
    {
        "type": "function",
        "function": {"name": "generate_image",
                     "description": "根据文字描述生成图片。当用户想要'画一张图'、'生成图片'时使用。",
                     "parameters": {"type": "object",
                                    "properties": {"prompt": {"type": "string", "description": "详细的图片描述"}},
                                    "required": ["prompt"]}},
        "meta": {"icon": "🎨", "label": "AI 画图"}
    }
]


def get_all_tools(user_id: int):
    tools = list(BUILTIN_TOOLS)
    for p in get_plugins(user_id):
        if not p.get('is_enabled'):
            continue
        tools.append({
            "type": "function",
            "function": {"name": p["name"], "description": p["description"],
                         "parameters": p["params_schema"] or {"type": "object", "properties": {}}},
            "meta": {"icon": "🧩", "label": p["name"], "plugin_id": p["id"]}
        })
    return tools


def execute_tool(name: str, arguments: dict, user_id: int):
    if name == "get_current_time":
        return get_current_time()
    elif name == "get_weather":
        return get_weather(**arguments)
    elif name == "calculate":
        return calculate(**arguments)
    elif name == "generate_image":
        return generate_image(arguments.get("prompt", ""), user_id)

    for p in get_plugins(user_id):
        if p["name"] == name:
            try:
                method = p.get("method", "GET").upper()
                url = p["url"]
                if method == "GET":
                    res = requests.get(url, params=arguments, timeout=15)
                else:
                    res = requests.post(url, json=arguments, timeout=15)
                try:
                    return res.json()
                except:
                    return {"result": res.text[:2000]}
            except Exception as e:
                return {"error": f"插件调用失败: {str(e)}"}
    return {"error": f"未知工具: {name}"}