import os
import importlib.util
import inspect
from typing import get_type_hints, get_origin, get_args

PLUGIN_DIR = os.path.join(os.path.dirname(__file__), "plugins")

# Python 类型 -> JSON Schema 类型
TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def python_type_to_json_schema(py_type):
    """把 Python 类型注解转成 JSON Schema 格式"""
    if py_type in TYPE_MAP:
        return {"type": TYPE_MAP[py_type]}
    origin = get_origin(py_type)
    if origin is not None:
        args = get_args(py_type)
        for arg in args:
            if arg is not type(None):
                return python_type_to_json_schema(arg)
    return {"type": "string"}


def extract_tool_from_function(func, namespace):
    """从 Python 函数自动提取工具定义"""
    sig = inspect.signature(func)
    hints = get_type_hints(func)
    doc = inspect.getdoc(func) or ""

    description = doc.split("\n")[0].strip() or func.__name__

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        if param_name in ("self", "cls"):
            continue
        py_type = hints.get(param_name, str)
        properties[param_name] = python_type_to_json_schema(py_type)
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    tool_name = f"{namespace}__{func.__name__}"
    tool = {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": f"[{namespace}] {description}",
            "parameters": {"type": "object", "properties": properties}
        }
    }
    if required:
        tool["function"]["parameters"]["required"] = required
    return tool


def load_plugins():
    """扫描 plugins 目录，动态加载所有插件"""
    plugins = []
    if not os.path.exists(PLUGIN_DIR):
        os.makedirs(PLUGIN_DIR, exist_ok=True)

    # 确保 __init__.py 存在
    init_file = os.path.join(PLUGIN_DIR, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w", encoding="utf-8"):
            pass

    for filename in sorted(os.listdir(PLUGIN_DIR)):
        if not filename.endswith(".py") or filename.startswith("_"):
            continue

        plugin_name = filename[:-3]
        filepath = os.path.join(PLUGIN_DIR, filename)

        try:
            spec = importlib.util.spec_from_file_location(f"plugins.{plugin_name}", filepath)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            meta = getattr(module, "PLUGIN_META", {
                "name": plugin_name,
                "label": plugin_name,
                "description": "无描述",
                "icon": "🔌",
                "author": "未知",
                "version": "1.0.0"
            })

            tools = []
            functions = []
            for fname, obj in inspect.getmembers(module, inspect.isfunction):
                if fname.startswith("_"):
                    continue
                if obj.__module__ != module.__name__:
                    continue
                try:
                    tool_def = extract_tool_from_function(obj, plugin_name)
                    tools.append(tool_def)
                    functions.append({
                        "tool_name": tool_def["function"]["name"],
                        "func": obj
                    })
                except Exception as e:
                    print(f"[Plugin] 解析 {plugin_name}.{fname} 失败: {e}")

            plugins.append({
                "meta": meta,
                "tools": tools,
                "functions": functions,
                "plugin_name": plugin_name
            })
            print(f"[Plugin] ✅ 加载插件 {plugin_name}，共 {len(tools)} 个工具")

        except Exception as e:
            print(f"[Plugin] ❌ 加载 {filename} 失败: {e}")

    return plugins