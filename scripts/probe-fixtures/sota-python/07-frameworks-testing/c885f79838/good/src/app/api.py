from fastapi import FastAPI

app = FastAPI()


@app.get("/users/{uid}", response_model=UserOut)
async def get_user(uid: int):
    return await db.get(User, uid)
