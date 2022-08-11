from typing import List

from fastapi import APIRouter, Form

from models import User, Post
from schemas import UploadPost, GetPost, Users

posts_router = APIRouter()



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
