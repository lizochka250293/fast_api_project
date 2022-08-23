from typing import List

import pydantic
from fastapi import APIRouter
from fastapi import Form, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from db import database, post_tags, posts, tags, users
from schemas import UploadPost, Users, GetUser, Tags, User, GetPost
from services import get_user
from tokenizator import create_token

posts_router = APIRouter()
templates = Jinja2Templates(directory='templates')

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@posts_router.get("/posts/", response_model=List[GetPost])
async def read_notes():
    query = posts.select()
    post = await database.fetch_all(query)
    return post


@posts_router.post("/post/", response_model=UploadPost)
async def create_post(
        title: str = Form(...),
        description: str = Form(...),
        username: str = Form(...),
        tag: List[str] = Form(...),
        user_cur: User = Depends(get_user)):
    query_user = users.select().where(users.c.username == username)
    last_record_id_user = await database.fetch_one(query_user)
    if not last_record_id_user:
        raise HTTPException(detail='User not found', status_code=401)
    id = last_record_id_user[0]
    try:
        cur = UploadPost(title=title, description=description, username=username)
    except pydantic.error_wrappers.ValidationError as e:
        raise HTTPException(detail=f'{e}', status_code=401)
    try:
        query = posts.insert().values(title=title, description=description, user_id=last_record_id_user[0])
        last_record = await database.execute(query)
    except:
        raise HTTPException(status_code=400, detail="Title already exists")
    cur_tag = tag[0].split(',')
    for i in cur_tag:
        query_tags = tags.select().where(tags.c.title == i)
        last_record_id_tag = await database.fetch_one(query_tags)
        if last_record_id_tag is None:
            query_tag = tags.insert().values(title=i)
            last_record = await database.execute(query_tag)
            query_posts_tags = post_tags.insert().values(tag_id=last_record,
                                                         post_id=last_record)
            last_record_posts_tags = await database.execute(query_posts_tags)
        else:
            query_posts_tags = post_tags.insert().values(tag_id=last_record_id_tag[0],
                                                         post_id=last_record)
            last_record_posts_tags = await database.execute(query_posts_tags)
    info = UploadPost(id=last_record, title=title, description=description, username=username, tags=cur_tag)
    return info


@posts_router.post("/user/")
async def create_user(username: str = Form(...),
                      email: str = Form(...),
                      password: str = Form(...),
                      replay_password: str = Form(...)):
    try:
        cur = Users(username=username, email=email, password=password)
    except pydantic.error_wrappers.ValidationError as e:
        raise HTTPException(detail=f'{e}', status_code=401)
    hash_password = pwd_context.hash(password)
    if pwd_context.verify(replay_password, hash_password):
        query_user = users.select().where(users.c.username == username)
        last_record_id_user = await database.fetch_one(query_user)
        query_email = users.select().where(users.c.email == email)
        last_record_id_email = await database.fetch_one(query_email)
        if not last_record_id_user:
            if not last_record_id_email:
                query = users.insert().values(username=username, email=email, password=hash_password)
                last_record = await database.execute(query)
                user = GetUser(id=last_record, username=username, email=email)
                return user
            raise HTTPException(detail=f'Пользователь с таким email существует', status_code=401)
        raise HTTPException(detail=f'Пользователь с таким именем существует', status_code=401)
    raise HTTPException(detail=f'Пароли не совпадают', status_code=401)


@posts_router.get('/posts/{post_pk}', response_class=HTMLResponse)
async def get_post(request: Request, post_pk: int, user_cur: User = Depends(get_user)):
    query = posts.select().where(posts.c.id == post_pk)
    post = await database.fetch_one(query)
    if not post:
        raise HTTPException(status_code=400, detail="Incorrect post_pk")
    user_id = post[-1]
    user = users.select().where(users.c.id == user_id)
    last_user = await database.fetch_one(user)
    q_tags = post_tags.select(post_tags.c.tag_id).where(post_tags.c.post_id == post_pk)
    _tags = await database.fetch_all(q_tags)
    id_tag = [i[1] for i in _tags]
    tags_list = []
    for i in id_tag:
        tag_i = tags.select().where(tags.c.id == i)
        tag = await database.fetch_one(tag_i)
        tags_list.append(tag)
    info_tag = [Tags(id=pk, tags=tag) for pk, tag in tags_list]
    return templates.TemplateResponse('index.html', {'request': request, 'title': post[1], 'description': post[2],
                                                     'info_tags': info_tag})


@posts_router.post("/login/")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_id = users.select().where(users.c.username == form_data.username)
    cur_user_id = await database.fetch_one(user_id)
    if not cur_user_id:
        raise HTTPException(status_code=400, detail="Incorrect username")
    if not pwd_context.verify(form_data.password, cur_user_id[3]):
        raise HTTPException(detail=f'Не верная пара логин пароль', status_code=401)
    else:
        return create_token(cur_user_id[0])


@posts_router.get("/users/me")
async def get_me(user_cur: User = Depends(get_user)):
    return user_cur


@posts_router.get('/users/{username}', response_model=GetUser)
async def get_user_1(username: str, user_cur: User = Depends(get_user)):
    query = users.select().where(users.c.username == username)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=400, detail="Incorect username")
    return user
