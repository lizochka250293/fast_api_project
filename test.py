from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
import os
from datetime import datetime, timedelta
from typing import Union, Any
from jose import jwt

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    }
}
#проверяем два пароля
def verify_password(plain_password, hashed_password):
    print(hashed_password)
    print(plain_password)
    print(pwd_context.verify(plain_password, hashed_password))
    return pwd_context.verify(plain_password, hashed_password)

#хэшируем пароль
def get_password_hash(password):
    print(pwd_context.hash(password))
    return pwd_context.hash(password)

# получаем пользователя
def get_user(db, username: str):
    if username in db:
        user = db[username]
        return user


def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    print(user['hashed_password'])
    if not user:
        return False
    if not verify_password(password, user['hashed_password']):
        return False
    print(user)
    return user


