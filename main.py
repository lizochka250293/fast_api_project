from typing import List

import databases
import pydantic
import sqlalchemy
from fastapi import FastAPI, Form, HTTPException

from schemas import UploadPost, Users, GetUserPosts, GetUser, User

app = FastAPI()

DATABASE_URL = "sqlite:///./test.db"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()
users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("username", sqlalchemy.String, unique=True),
    sqlalchemy.Column("email", sqlalchemy.String, unique=True),
    sqlalchemy.Column("password", sqlalchemy.String)
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

engine = sqlalchemy.create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)


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


@app.post("/post/", response_model=GetUserPosts)
async def create_note(
        title: str = Form(...), description: str = Form(...), username: str = Form(...), tag: List[str] = Form(...)
):
    query_user = users.select().where(users.c.username == username)
    last_record_id_user = await database.fetch_one(query_user)
    if last_record_id_user is None:
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
    info = GetUserPosts(id=last_record, title=title, description=description, username=username)
    return info

#как проверить что не None?
@app.post("/user/")
async def create_user(username: str = Form(...),
                      email: str = Form(...),
                      password: str = Form(...),
                      replay_password: str = Form(...)):
    try:
        cur = Users(username=username, email=email, password=password)
        print(cur)
        return cur
    except pydantic.error_wrappers.ValidationError as e:
        raise HTTPException(detail=f'{e}', status_code=401)

        # query = users.insert().values(username=username)
        # last_record_id = await database.execute(query)
        # info = Users(id=last_record_id, username=username)




@app.get('/users/{username}', response_model=GetUser)
async def get_post(username: str):
    query = users.select().where(users.c.username == username)
    # if not query:
    #     raise HTTPException(status_code=400, detail="Incorrect username")
    return await database.fetch_one(query)


@app.get('/posts/{post_pk}', response_model=GetUserPosts)
async def get_post(post_pk: int):
    query = posts.select().where(posts.c.id == post_pk)
    return await database.fetch_one(query)
