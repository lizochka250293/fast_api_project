from fastapi import FastAPI
from starlette.templating import Jinja2Templates

from api import posts_router
from db import database

app = FastAPI()
templates = Jinja2Templates(directory='templates')


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


app.include_router(posts_router)
