from fastapi import FastAPI
app = FastAPI()


@app.get('/')
async def title():
    return {'message': 'Hello word'}
