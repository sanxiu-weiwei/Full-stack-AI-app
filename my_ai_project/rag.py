import os
import base64
import chromadb
from pypdf import PdfReader
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv
from llm_factory import get_client, get_embedding_model, get_vision_model

load_dotenv(override=True)

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")
chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)


def get_embedding(text: str, user_id: int):
    model = get_embedding_model(user_id)
    if not model:
        raise ValueError("当前模型配置不支持向量化，无法使用文档问答功能")
    client = get_client(user_id)
    resp = client.embeddings.create(model=model, input=text[:2000])
    return resp.data[0].embedding


def extract_pdf(file_path):
    reader = PdfReader(file_path)
    return "\n".join([(page.extract_text() or "") for page in reader.pages])


def extract_txt(file_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read()


def extract_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_image(file_path, user_id: int):
    vision_model = get_vision_model(user_id)
    if not vision_model:
        raise ValueError("当前模型配置不支持图片理解")
    client = get_client(user_id)
    with open(file_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    response = client.chat.completions.create(
        model=vision_model,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "请详细描述这张图片的所有内容，包括物体、文字、场景。这段描述将用于知识库检索。"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]
        }]
    )
    return response.choices[0].message.content


def process_file(file_path: str, ext: str, user_id: int) -> str:
    ext = ext.lower().lstrip('.')
    if ext == 'pdf':
        return extract_pdf(file_path)
    elif ext in ['txt', 'md', 'markdown']:
        return extract_txt(file_path)
    elif ext == 'docx':
        return extract_docx(file_path)
    elif ext in ['png', 'jpg', 'jpeg', 'webp']:
        return extract_image(file_path, user_id)
    else:
        raise ValueError(f"暂不支持的文件类型: {ext}")


def index_file(file_path: str, ext: str, user_id: int, doc_id: int):
    full_text = process_file(file_path, ext, user_id)
    if not full_text.strip():
        raise ValueError("无法从该文件中提取到有效内容")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", ".", " ", ""]
    )
    chunks = splitter.split_text(full_text)

    collection_name = f"user_{user_id}_doc_{doc_id}"
    collection = chroma_client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

    BATCH = 16
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i:i + BATCH]
        embeddings = [get_embedding(c, user_id) for c in batch]
        ids = [f"chunk_{i + j}" for j in range(len(batch))]
        collection.add(embeddings=embeddings, documents=batch, ids=ids)
    return len(chunks)


def search_chunks(query: str, user_id: int, doc_ids: list, top_k: int = 3):
    if not doc_ids:
        return []
    query_emb = get_embedding(query, user_id)
    all_results = []
    for doc_id in doc_ids:
        try:
            collection = chroma_client.get_collection(name=f"user_{user_id}_doc_{doc_id}")
            results = collection.query(query_embeddings=[query_emb], n_results=top_k)
            if results["documents"] and results["documents"][0]:
                for doc, dist in zip(results["documents"][0], results["distances"][0]):
                    all_results.append({"content": doc, "distance": dist})
        except Exception as e:
            print(f"[RAG] 检索失败: {e}")
    all_results.sort(key=lambda x: x["distance"])
    return all_results[:top_k]


def delete_document_vectors(user_id: int, doc_id: int):
    try:
        chroma_client.delete_collection(name=f"user_{user_id}_doc_{doc_id}")
    except Exception:
        pass