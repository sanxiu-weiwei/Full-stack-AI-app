import os
import pymysql
import json
from dotenv import load_dotenv

load_dotenv(override=True)


def get_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST"), port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"), charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


# ========== 消息 ==========
def save_message(session_id: str, role: str, content: str):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
                           (session_id, role, content))
        conn.commit()
    finally:
        conn.close()


def load_messages(session_id: str, limit: int = 50):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT role, content FROM messages WHERE session_id = %s AND role IN ('user','assistant','system') ORDER BY id ASC LIMIT %s",
                (session_id, limit))
            return cursor.fetchall()
    finally:
        conn.close()


# ========== 用户 ==========
def get_user_by_username(username: str):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cursor.fetchone()
    finally:
        conn.close()


def create_user(username: str, password_hash: str):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def update_user_logo(user_id: int, logo_url: str):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE users SET logo_url = %s WHERE id = %s", (logo_url, user_id))
        conn.commit()
    finally:
        conn.close()


# ========== 会话 ==========
def get_sessions(user_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            sql = """
            SELECT session_id, MAX(created_at) AS last_time,
                (SELECT content FROM messages m2 WHERE m2.session_id = m1.session_id AND m2.role = 'title' ORDER BY id DESC LIMIT 1) AS custom_title,
                (SELECT content FROM messages m3 WHERE m3.session_id = m1.session_id AND m3.role = 'user' ORDER BY id ASC LIMIT 1) AS preview
            FROM messages m1 WHERE session_id LIKE %s AND role != 'title'
            GROUP BY session_id ORDER BY last_time DESC
            """
            cursor.execute(sql, (f"user_{user_id}_session_%",))
            rows = cursor.fetchall()
            for r in rows:
                r["preview"] = r.get("custom_title") or r.get("preview")
            return rows
    finally:
        conn.close()


def rename_session(session_id: str, new_title: str):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM messages WHERE session_id = %s AND role = 'title'", (session_id,))
            cursor.execute("INSERT INTO messages (session_id, role, content) VALUES (%s, 'title', %s)",
                           (session_id, new_title))
        conn.commit()
    finally:
        conn.close()


def delete_session(session_id: str):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM messages WHERE session_id = %s", (session_id,))
        conn.commit()
    finally:
        conn.close()


def get_session_title(session_id: str):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT content FROM messages WHERE session_id = %s AND role = 'title' LIMIT 1",
                           (session_id,))
            row = cursor.fetchone()
            return row["content"] if row else None
    finally:
        conn.close()


# ========== 文档 ==========
def create_document(user_id: int, filename: str, chunk_count: int = 0, file_type: str = 'file',
                    status: str = 'pending'):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO documents (user_id, filename, chunk_count, file_type, status) VALUES (%s, %s, %s, %s, %s)",
                (user_id, filename, chunk_count, file_type, status))
            new_id = cursor.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


def update_document_status(doc_id: int, status: str, chunk_count: int = None, error_msg: str = None):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            if chunk_count is not None:
                cursor.execute("UPDATE documents SET status = %s, chunk_count = %s, error_msg = %s WHERE id = %s",
                               (status, chunk_count, error_msg, doc_id))
            else:
                cursor.execute("UPDATE documents SET status = %s, error_msg = %s WHERE id = %s",
                               (status, error_msg, doc_id))
        conn.commit()
    finally:
        conn.close()


def list_documents(user_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, filename, chunk_count, file_type, status, error_msg, created_at FROM documents WHERE user_id = %s ORDER BY id DESC",
                (user_id,))
            rows = cursor.fetchall()
            for r in rows:
                r['file_type'] = r.get('file_type') or 'file'
                r['status'] = r.get('status') or 'done'
            return rows
    finally:
        conn.close()


def get_document(doc_id: int, user_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM documents WHERE id = %s AND user_id = %s", (doc_id, user_id))
            return cursor.fetchone()
    finally:
        conn.close()


def delete_document(doc_id: int, user_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM documents WHERE id = %s AND user_id = %s", (doc_id, user_id))
        conn.commit()
    finally:
        conn.close()


# ========== 插件 ==========
def add_plugin(user_id: int, name: str, description: str, method: str, url: str, params_schema: dict):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO custom_plugins (user_id, name, description, method, url, params_schema) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, name, description, method, url, json.dumps(params_schema, ensure_ascii=False)))
            new_id = cursor.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


def get_plugins(user_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM custom_plugins WHERE user_id = %s ORDER BY id DESC", (user_id,))
            rows = cursor.fetchall()
            for r in rows:
                r['params_schema'] = json.loads(r['params_schema']) if r['params_schema'] else {}
            return rows
    finally:
        conn.close()


def delete_plugin(plugin_id: int, user_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM custom_plugins WHERE id = %s AND user_id = %s", (plugin_id, user_id))
        conn.commit()
    finally:
        conn.close()


# ========== LLM 配置 ==========
def create_llm_config(user_id: int, name: str, api_key: str, base_url: str,
                      chat_model: str, embedding_model: str = None,
                      vision_model: str = None, image_model: str = None):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            # 如果这是用户的第一个配置，自动激活
            cursor.execute("SELECT COUNT(*) AS cnt FROM llm_configs WHERE user_id = %s", (user_id,))
            is_first = cursor.fetchone()["cnt"] == 0

            cursor.execute(
                """INSERT INTO llm_configs (user_id, name, api_key, base_url, chat_model, embedding_model, vision_model, image_model, is_active)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (user_id, name, api_key, base_url, chat_model, embedding_model, vision_model, image_model,
                 1 if is_first else 0)
            )
            new_id = cursor.lastrowid
        conn.commit()
        return new_id
    finally:
        conn.close()


def list_llm_configs(user_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM llm_configs WHERE user_id = %s ORDER BY id DESC", (user_id,))
            rows = cursor.fetchall()
            # API Key 脱敏
            for r in rows:
                key = r.get("api_key") or ""
                r["api_key_masked"] = f"{key[:6]}...{key[-4:]}" if len(key) > 12 else "****"
                r.pop("api_key", None)  # 不返回明文
            return rows
    finally:
        conn.close()


def get_active_llm_config(user_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM llm_configs WHERE user_id = %s AND is_active = 1 LIMIT 1", (user_id,))
            return cursor.fetchone()
    finally:
        conn.close()


def get_llm_config(config_id: int, user_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM llm_configs WHERE id = %s AND user_id = %s", (config_id, user_id))
            return cursor.fetchone()
    finally:
        conn.close()


def update_llm_config(config_id: int, user_id: int, name: str, api_key: str, base_url: str,
                      chat_model: str, embedding_model: str = None,
                      vision_model: str = None, image_model: str = None):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """UPDATE llm_configs SET name=%s, api_key=%s, base_url=%s, chat_model=%s,
                   embedding_model=%s, vision_model=%s, image_model=%s
                   WHERE id=%s AND user_id=%s""",
                (name, api_key, base_url, chat_model, embedding_model, vision_model, image_model, config_id, user_id)
            )
        conn.commit()
    finally:
        conn.close()


def activate_llm_config(config_id: int, user_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE llm_configs SET is_active = 0 WHERE user_id = %s", (user_id,))
            cursor.execute("UPDATE llm_configs SET is_active = 1 WHERE id = %s AND user_id = %s", (config_id, user_id))
        conn.commit()
    finally:
        conn.close()


def delete_llm_config(config_id: int, user_id: int):
    conn = get_conn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM llm_configs WHERE id = %s AND user_id = %s", (config_id, user_id))
        conn.commit()
    finally:
        conn.close()