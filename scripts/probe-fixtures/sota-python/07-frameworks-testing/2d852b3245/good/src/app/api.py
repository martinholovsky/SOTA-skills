from fastapi import FastAPI

app = FastAPI()


@app.get("/livez")
async def live():
    return {"ok": True}
