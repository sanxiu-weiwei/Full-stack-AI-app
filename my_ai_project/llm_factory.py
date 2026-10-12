import os
from openai import OpenAI
from dotenv import load_dotenv
from db import get_active_llm_config

load_dotenv(override=True)

# 简单的内存缓存：{user_id: config_dict}
_cache = {}


def _default_config():
    """用户没配置时，从 .env 读兜底配置"""
    return {
        "id": 0,
        "name": "默认配置(.env)",
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": "https://open.bigmodel.cn/api/paas/v4/",
        "chat_model": "glm-4-flash",
        "embedding_model": "embedding-3",
        "vision_model": "glm-4v",
        "image_model": "cogview-3-flash",
    }


def get_user_config(user_id: int) -> dict:
    """获取用户当前激活的配置（带缓存）"""
    if user_id in _cache:
        return _cache[user_id]
    cfg = get_active_llm_config(user_id)
    if not cfg:
        cfg = _default_config()
    _cache[user_id] = cfg
    return cfg


def clear_cache(user_id: int = None):
    """配置变更时清缓存"""
    global _cache
    if user_id is None:
        _cache = {}
    else:
        _cache.pop(user_id, None)


def get_client(user_id: int) -> OpenAI:
    cfg = get_user_config(user_id)
    return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])


def get_chat_model(user_id: int) -> str:
    return get_user_config(user_id)["chat_model"]


def get_embedding_model(user_id: int):
    return get_user_config(user_id).get("embedding_model")


def get_vision_model(user_id: int):
    return get_user_config(user_id).get("vision_model")


def get_image_model(user_id: int):
    return get_user_config(user_id).get("image_model")