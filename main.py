
from datetime import datetime, timedelta
from typing import List, Union
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
import databases
import pydantic
import sqlalchemy
from fastapi import FastAPI, Form, HTTPException, Depends
from pydantic import BaseModel
from starlette import status
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from schemas import UploadPost, Users, GetUserPosts, GetUser, User, UserInDB, Token, TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI()
templates = Jinja2Templates(directory='templates')
DATABASE_URL = "sqlite:///./test.db"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()
users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("username", sqlalchemy.String, unique=True),
    sqlalchemy.Column("email", sqlalchemy.String, unique=True),
    sqlalchemy.Column("password", sqlalchemy.String),
    sqlalchemy.Column(
        "is_active",
        sqlalchemy.Boolean(),
        server_default=sqlalchemy.sql.expression.false(),
        nullable=False,
    )
)

tags = sqlalchemy.Table(
    "tags",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("title", sqlalchemy.String, unique=True),
)

posts = sqlalchemy.Table(
    "posts",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("title", sqlalchemy.String, unique=True),
    sqlalchemy.Column("description", sqlalchemy.String),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey(users.c.id))

)

post_tags = sqlalchemy.Table(
    "post_tags",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("tag_id", sqlalchemy.ForeignKey(tags.c.id)),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey(users.c.id)),
    sqlalchemy.Column("post_id", sqlalchemy.ForeignKey(posts.c.id))
)

tokens_table = sqlalchemy.Table(
    "tokens",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column(
        "token",
        sqlalchemy.String,
        unique=True,
        nullable=False,
        index=True,
    ),
    sqlalchemy.Column("expires", sqlalchemy.DateTime()),
    sqlalchemy.Column("user_id", sqlalchemy.ForeignKey("users.id")),
)
engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    user_token = tokens_table.select().where(tokens_table.c.token == token, tokens_table.c.expires > datetime.now())
    user = await database.fetch_one(user_token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/posts/", response_model=List[UploadPost])
async def read_notes():
    query = posts.select()
    return await database.fetch_all(query)


@app.post("/post/", response_model=UploadPost)
async def create_post(
        title: str = Form(...), description: str = Form(...), username: str = Form(...), tag: List[str] = Form(...)
):
    query_user = users.select().where(users.c.username == username)
    last_record_id_user = await database.fetch_one(query_user)
    if not last_record_id_user:
        raise HTTPException(detail='User not found', status_code=401)
    id = last_record_id_user[0]
    try:
        cur = UploadPost(title=title, description=description, tags=tag)
    except pydantic.error_wrappers.ValidationError as e:
        raise HTTPException(detail=f'{e}', status_code=401)
    try:
        query = posts.insert().values(title=title, description=description, user_id=id)
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
            query_posts_tags = post_tags.insert().values(tag_id=last_record, user_id=last_record_id_user[0], post_id=last_record)
            last_record_posts_tags = await database.execute(query_posts_tags)
        else:
            query_posts_tags = post_tags.insert().values(tag_id=last_record_id_tag[0], user_id=last_record_id_user[0], post_id=last_record)
            last_record_posts_tags = await database.execute(query_posts_tags)
    info = UploadPost(id=last_record, title=title, description=description, username=username, tags=tags)
    return info

#как проверить pdmodel?
@app.post("/user/")
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



@app.get('/users/{username}', response_model=GetUser)
async def get_user_1(username: str, user: User = Depends(get_current_user)):
    query = users.select().where(users.c.username == username)
    user = await database.fetch_one(query)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username")
    info = GetUser(id=user[0], username=user[1], email=user[2])
    return info


@app.get('/posts/{post_pk}', response_class=HTMLResponse)
async def get_post(request: Request, post_pk: int):
    query = posts.select().where(posts.c.id == post_pk)
    post = await database.fetch_one(query)
    if not post:
        raise HTTPException(status_code=400, detail="Incorrect post_pk")
    user_id = post[-1]
    user = users.select().where(users.c.id == user_id)
    last_user = await database.fetch_one(user)
    info = GetUserPosts(username=str(last_user[1]), id=post[0], title=post[1], description=post[2])
    return templates.TemplateResponse('index.html', {'request': request, 'title': post[1], 'description': post[2]})

# как update?
@app.post("/login/")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user_id = users.select().where(users.c.username == form_data.username)
    cur_user_id = await database.fetch_one(user_id)
    if not cur_user_id:
            raise HTTPException(status_code=400, detail="Incorrect username")
    if not pwd_context.verify(form_data.password, cur_user_id[3]):
        raise HTTPException(detail=f'Не верная пара логин пароль', status_code=401)
    else:
        search_token = tokens_table.select().where(tokens_table.c.user_id == cur_user_id[0])
        cur_user = await database.fetch_one(search_token)
        if cur_user:
            expires_delta = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            to_encode = {"exp": expires_delta, "sub": str(form_data.username)}
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            query = (
                tokens_table.update()
                .values(expires=expires_delta, user_id=cur_user_id[0]))
            new_token = await database.fetch_one(query)
            user_token = Token(access_token=encoded_jwt)
        else:
            expires_delta = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            to_encode = {"exp": expires_delta, "sub": str(form_data.username)}
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            query = (
                tokens_table.insert()
                .values(expires=expires_delta, user_id=cur_user_id[0], token=encoded_jwt))
            new_token = await database.fetch_one(query)
            user_token = Token(access_token=encoded_jwt)
        return user_token



@app.get("/users/me")
async def get_me(user: User = Depends(get_current_user)):
    return user
