import jwt
from fastapi import HTTPException, Security
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from starlette.status import HTTP_403_FORBIDDEN

from db import database, users
from schemas import User, TokenPayload
from tokenizator import ALGORITHM, SECRET_KEY

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/login")


async def get_current_user(token: str = Security(reusable_oauth2)):
    """ Check auth user
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)
    except PyJWTError:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )
    user = users.select().where(users.c.id == token_data.user_id)
    last_record_id_user = await database.fetch_one(user)
    if not last_record_id_user:
        raise HTTPException(status_code=404, detail="User not found")
    return last_record_id_user[1]


async def get_user(current_user: User = Security(get_current_user)):
    """ Проверка юзер """
    if not current_user:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
