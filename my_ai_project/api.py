import os
import json
import shutil
import time
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from db import (
    save_message, load_messages, get_user_by_username, create_user,
    get_sessions, rename_session, delete_session,
    create_document, list_documents, get_document, delete_document,
    update_document_status, add_plugin, get_plugins, delete_plugin,
    update_user_logo,
    create_llm_config, list_llm_configs, get_active_llm_config,
    update_llm_config, activate_llm_config, delete_llm_config
)
from auth import verify_password, get_password_hash, create_access_token, get_current_user
from tools import get_all_tools, execute_tool
from rag import index_file, search_chunks, delete_document_vectors
from llm_factory import get_client, get_chat_model, clear_cache

load_dotenv(override=True)

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(__file__)
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
LOGO_DIR = os.path.join(UPLOAD_DIR, "logos")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(LOGO_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

ALLOWED_EXTS = ['pdf', 'txt', 'md', 'markdown', 'docx', 'png', 'jpg', 'jpeg', 'webp']
ALLOWED_LOGO_EXTS = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg', 'avif', 'bmp', 'ico', 'tif', 'tiff', 'heic', 'heif']


# ============ 数据模型 ============
class UserAuth(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    session_id: str
    message: str
    doc_ids: list = []
    use_tools: bool = True
    enabled_tools: list = []

class RenameRequest(BaseModel):
    new_title: str

class PluginRequest(BaseModel):
    name: str
    description: str
    method: str = "GET"
    url: str
    params_schema: dict = {}

class LLMConfigRequest(BaseModel):
    name: str
    api_key: str
    base_url: str
    chat_model: str
    embedding_model: str = None
    vision_model: str = None
    image_model: str = None


# ============ 用户认证 ============
@app.post("/register")
def register(user: UserAuth):
    if get_user_by_username(user.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    create_user(user.username, get_password_hash(user.password))
    return {"message": "注册成功"}


@app.post("/login")
def login(user: UserAuth):
    db_user = get_user_by_username(user.username)
    if not db_user or not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(data={"sub": db_user["username"]})
    return {"access_token": token, "token_type": "bearer",
            "username": db_user["username"], "logo_url": db_user.get("logo_url")}


@app.get("/user/profile")
def get_profile(current_user: dict = Depends(get_current_user)):
    return {"username": current_user["username"], "logo_url": current_user.get("logo_url")}


@app.post("/user/logo")
async def upload_logo(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    filename = file.filename or ""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_LOGO_EXTS:
        raise HTTPException(status_code=400, detail=f"不支持的图片格式 .{ext}")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片超过 5MB 限制")
    safe_name = f"logo_user_{current_user['id']}_{int(time.time())}.{ext}"
    with open(os.path.join(LOGO_DIR, safe_name), "wb") as f:
        f.write(content)
    logo_url = f"/static/logos/{safe_name}"
    update_user_logo(current_user['id'], logo_url)
    return {"logo_url": logo_url}


@app.delete("/user/logo")
def delete_logo(current_user: dict = Depends(get_current_user)):
    update_user_logo(current_user['id'], None)
    return {"message": "已重置"}


# ============ 🌟 LLM 配置管理 ============
@app.get("/llm/configs")
def api_list_configs(current_user: dict = Depends(get_current_user)):
    return list_llm_configs(current_user["id"])


@app.post("/llm/configs")
def api_create_config(req: LLMConfigRequest, current_user: dict = Depends(get_current_user)):
    cfg_id = create_llm_config(
        current_user["id"], req.name, req.api_key, req.base_url, req.chat_model,
        req.embedding_model, req.vision_model, req.image_model
    )
    clear_cache(current_user["id"])
    return {"message": "已添加", "id": cfg_id}


@app.put("/llm/configs/{config_id}")
def api_update_config(config_id: int, req: LLMConfigRequest, current_user: dict = Depends(get_current_user)):
    update_llm_config(
        config_id, current_user["id"], req.name, req.api_key, req.base_url,
        req.chat_model, req.embedding_model, req.vision_model, req.image_model
    )
    clear_cache(current_user["id"])
    return {"message": "已更新"}


@app.post("/llm/configs/{config_id}/activate")
def api_activate_config(config_id: int, current_user: dict = Depends(get_current_user)):
    activate_llm_config(config_id, current_user["id"])
    clear_cache(current_user["id"])
    return {"message": "已切换"}


@app.delete("/llm/configs/{config_id}")
def api_delete_config(config_id: int, current_user: dict = Depends(get_current_user)):
    delete_llm_config(config_id, current_user["id"])
    clear_cache(current_user["id"])
    return {"message": "已删除"}


# ============ 插件 ============
@app.get("/plugins")
def get_user_plugins(current_user: dict = Depends(get_current_user)):
    return get_plugins(current_user["id"])


@app.post("/plugins")
def create_plugin(req: PluginRequest, current_user: dict = Depends(get_current_user)):
    return {"id": add_plugin(current_user["id"], req.name, req.description, req.method, req.url, req.params_schema)}


@app.delete("/plugins/{plugin_id}")
def remove_plugin(plugin_id: int, current_user: dict = Depends(get_current_user)):
    delete_plugin(plugin_id, current_user["id"])
    return {"message": "已删除"}


# ============ 文档 ============
def process_document_background(doc_id: int, user_id: int, file_path: str, ext: str):
    try:
        update_document_status(doc_id, "processing")
        chunk_count = index_file(file_path, ext, user_id, doc_id)
        update_document_status(doc_id, "done", chunk_count=chunk_count)
    except Exception as e:
        update_document_status(doc_id, "failed", error_msg=str(e)[:500])


@app.post("/upload")
async def upload_file(background_tasks: BackgroundTasks, file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    filename = file.filename or ""
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"支持格式: {', '.join(ALLOWED_EXTS)}")
    safe_name = f"user_{current_user['id']}_{int(time.time())}_{filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    doc_id = create_document(current_user["id"], filename, 0, ext, status="pending")
    background_tasks.add_task(process_document_background, doc_id, current_user["id"], file_path, ext)
    return {"message": "上传成功", "doc_id": doc_id}


@app.get("/documents")
def get_documents(current_user: dict = Depends(get_current_user)):
    return list_documents(current_user["id"])


@app.delete("/documents/{doc_id}")
def remove_document(doc_id: int, current_user: dict = Depends(get_current_user)):
    doc = get_document(doc_id, current_user["id"])
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    delete_document_vectors(current_user["id"], doc_id)
    delete_document(doc_id, current_user["id"])
    return {"message": "已删除"}


# ============ 会话 ============
@app.get("/sessions")
def get_sessions_api(current_user: dict = Depends(get_current_user)):
    return get_sessions(current_user["id"])


@app.put("/sessions/{session_id}/rename")
def rename(session_id: str, req: RenameRequest, current_user: dict = Depends(get_current_user)):
    rename_session(f"user_{current_user['id']}_{session_id}", req.new_title)
    return {"message": "重命名成功"}


@app.delete("/sessions/{session_id}")
def delete(session_id: str, current_user: dict = Depends(get_current_user)):
    delete_session(f"user_{current_user['id']}_{session_id}")
    return {"message": "删除成功"}


@app.get("/history/{session_id}")
def history(session_id: str, current_user: dict = Depends(get_current_user)):
    return load_messages(f"user_{current_user['id']}_{session_id}")


# ============ 聊天 ============
@app.post("/chat")
def chat(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    real_session_id = f"user_{user_id}_{req.session_id}"
    save_message(real_session_id, "user", req.message)
    history = load_messages(real_session_id)

    system_content = "你是一个乐于助人的编程助手。"
    used_rag = False

    if req.doc_ids:
        valid = [d for d in req.doc_ids if (get_document(d, user_id) or {}).get("status") == "done"]
        if valid:
            try:
                chunks = search_chunks(req.message, user_id, valid, top_k=3)
                if chunks:
                    used_rag = True
                    context = "\n\n".join([f"【片段{i+1}】{c['content']}" for i, c in enumerate(chunks)])
                    system_content += f"\n\n下面是从文档中检索到的相关内容：\n\n{context}"
            except Exception as e:
                print(f"[RAG] {e}")

    messages = [{"role": "system", "content": system_content}] + history

    tools_param = None
    if req.use_tools:
        all_tools = get_all_tools(user_id)
        tools_param = [t for t in all_tools if t["function"]["name"] in req.enabled_tools] if req.enabled_tools else all_tools
        if not tools_param:
            tools_param = None

    # 🌟 动态获取客户端和模型名
    client = get_client(user_id)
    chat_model = get_chat_model(user_id)

    def sse(data: dict):
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    def generate():
        if used_rag:
            yield sse({"type": "info", "content": "📚 已检索文档"})
        final_reply = ""
        for _ in range(5):
            stream = client.chat.completions.create(
                model=chat_model, messages=messages, tools=tools_param, stream=True
            )
            content_buffer = ""
            tool_calls_buffer = {}
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    content_buffer += delta.content
                    yield sse({"type": "content", "content": delta.content})
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_calls_buffer:
                            tool_calls_buffer[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc.id: tool_calls_buffer[idx]["id"] = tc.id
                        if tc.function:
                            if tc.function.name: tool_calls_buffer[idx]["name"] = tc.function.name
                            if tc.function.arguments: tool_calls_buffer[idx]["arguments"] += tc.function.arguments

            if not tool_calls_buffer:
                final_reply = content_buffer
                break

            assistant_msg = {"role": "assistant", "content": content_buffer or None, "tool_calls": []}
            for idx in sorted(tool_calls_buffer.keys()):
                tc = tool_calls_buffer[idx]
                assistant_msg["tool_calls"].append({
                    "id": tc["id"], "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]}
                })
            messages.append(assistant_msg)

            for idx in sorted(tool_calls_buffer.keys()):
                tc = tool_calls_buffer[idx]
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except Exception:
                    args = {}
                yield sse({"type": "tool_call", "name": tc["name"], "args": args})
                result = execute_tool(tc["name"], args, user_id)
                if tc["name"] == "generate_image" and isinstance(result, dict) and result.get("image_url"):
                    yield sse({"type": "image", "url": result["image_url"], "prompt": result.get("prompt", "")})
                yield sse({"type": "tool_result", "name": tc["name"], "result": result})
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": json.dumps(result, ensure_ascii=False)})

        if final_reply:
            save_message(real_session_id, "assistant", final_reply)
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")