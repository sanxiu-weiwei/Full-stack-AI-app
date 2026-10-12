import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from db import get_user_by_username

# 生产环境建议把 SECRET_KEY 写到 .env 文件里，这里为了教学简单直接硬编码
SECRET_KEY = "your-super-secret-key-change-this-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 天有效期

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 告诉 FastAPI，token 要从请求头的 Authorization: Bearer <token> 里取
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def verify_password(plain_password, hashed_password):
    """校验密码，并在校验前截断至 72 字节，防止 bcrypt 崩溃"""
    # 将明文密码编码为字节并截断
    plain_bytes = plain_password.encode('utf-8')[:72]
    # 重新解码为字符串（忽略截断产生的坏字节）
    safe_password = plain_bytes.decode('utf-8', errors='ignore')
    return pwd_context.verify(safe_password, hashed_password)


def get_password_hash(password):
    """生成密码哈希，并在加密前截断至 72 字节，防止 bcrypt 崩溃"""
    password_bytes = password.encode('utf-8')[:72]
    safe_password = password_bytes.decode('utf-8', errors='ignore')
    return pwd_context.hash(safe_password)


def create_access_token(data: dict):
    """生成 JWT Token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """依赖注入：从 Token 中解析当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的登录凭证，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user