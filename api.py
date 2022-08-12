from typing import List

from fastapi import APIRouter, Form
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import Jinja2Templates

from models import User, Post
from schemas import UploadPost, GetPost, Users, GetUserPosts

posts_router = APIRouter()
templates = Jinja2Templates(directory='templates')


@posts_router.post('/', response_model=UploadPost)
async def post_set(title: str = Form(...), description: str = Form(...)):
    info = UploadPost(title=title, description=description)
    user = await User.objects.first()
    return await Post.objects.create(user=user, **info.dict())


@posts_router.post("/user/", response_model=Users)
async def create_user(user: User):
    await user.save()
    return user


@posts_router.post("/posts/", response_model=Post)
async def create_post(post: Post):
    await post.save()
    return post


@posts_router.get('/posts/{post_pk}', response_model=GetPost)
async def get_post(post_pk: int):
    return await Post.objects.select_related('user').get(pk=post_pk)


@posts_router.get('/user/{user_pk}', response_model=List[GetUserPosts])
async def get_users_posts(user_pk: int):
    posts_list = await Post.objects.filter(user=user_pk).all()
    return posts_list


@posts_router.get('/index/{post_pk}', response_class=HTMLResponse)
async def get_post_list(request: Request, post_pk: int):
    post = Post.objects.get(pk=post_pk)
    #мне казалось мы получаем обьект
    return templates.TemplateResponse('index.html', {'request': request, 'post': post})
