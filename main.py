from datetime import datetime, timedelta
from typing import List
import jwt
from jwt import PyJWTError
from fastapi import HTTPException, Security
from starlette.status import HTTP_403_FORBIDDEN
from tokenizator import ALGORITHM, SECRET_KEY
from schemas import TokenPayload, User
import databases
import pydantic
import sqlalchemy
from fastapi import FastAPI, Form, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from starlette import status
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates
from schemas import UploadPost, Users, GetUser, Tags
from tokenizator import create_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
# ALGORITHM = "HS256"
# access_token_jwt_subject = "access"
# ACCESS_TOKEN_EXPIRE_MINUTES = 60
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/login/access-token")
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
        server_default=sqlalchemy.sql.expression.true(),
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


async def get_current_user(token: str = Security(reusable_oauth2)):
    """ Check auth user
    """
    print(token)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(payload)
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
    """ Проверка активный юзер или нет """
    print(current_user)
    if not current_user:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

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
    print(last_record_id_user)
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


# как проверить pdmodel?
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
async def get_user_1(username: str):
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
    q_tags = post_tags.select(post_tags.c.tag_id).where(post_tags.c.post_id == post_pk)
    _tags = await database.fetch_all(q_tags)
    id_tag = [i[1] for i in _tags]
    tags_list = []
    for i in id_tag:
        tag_i = tags.select().where(tags.c.id == i)
        tag = await database.fetch_one(tag_i)
        tags_list.append(tag)
    info_tag = [Tags(id=pk, tags=tag) for pk, tag in tags_list]
    return templates.TemplateResponse('index.html', {'request': request, 'title': post[1], 'description': post[2], 'info_tags': info_tag})


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
        return create_token(cur_user_id[0])


@app.get("/users/me")
async def get_me(user_cur: User = Depends(get_user)):
    print(user_cur)
    return user_cur
