from typing import List
from forbidden_words import forbidden_words
from pydantic import BaseModel, Field, validator

class Users(BaseModel):
    id: int
    username: str = Field(..., max_length=20, min_length=2,
                       description='The name of the article should not be less than 2 and more than 20 characters')


class UploadPost(BaseModel):
    title: str = Field(..., max_length=50, min_length=3,
                       description='The title of the article should not be less than 3 and more than 50 characters')
    description: str = Field(..., max_length=1500, min_length=3,
                       description='The description of the article should not be less than 3 and more than 1500 characters')

    tags: List[str] = None

    @validator('description', 'title')
    def check_description(cls, v):
        for word in forbidden_words:
            if word in v:
                raise ValueError('В описании не должно быть мата')
        return v


class GetPost(BaseModel):
    user: Users
    title: str
    description: str


class GetUserPosts(BaseModel):
    id: int
    title: str
    description: str
