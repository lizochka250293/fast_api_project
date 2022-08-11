import datetime
from typing import Optional

import ormar

from db import metadata, database


class MainMeta(ormar.ModelMeta):
    metadata = metadata
    database = database


class User(ormar.Model):
    class Meta(MainMeta):
        tablename = "users"

    id = ormar.Integer(primary_key=True)
    username = ormar.String(max_length=50, unique=True)


class Post(ormar.Model):
    class Meta(MainMeta):
        pass

    id = ormar.Integer(primary_key=True)
    title = ormar.String(max_length=50, unique=True)
    description = ormar.String(max_length=1500)
    tags = ormar.String(max_length=500, default='')
    user: Optional[User] = ormar.ForeignKey(User)




