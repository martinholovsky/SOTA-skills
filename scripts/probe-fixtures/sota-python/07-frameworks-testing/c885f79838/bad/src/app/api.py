from fastapi import FastAPI

app = FastAPI()


@app.get("/users/{uid}")
async def get_user(uid: int):
    return await db.get(User, uid)
