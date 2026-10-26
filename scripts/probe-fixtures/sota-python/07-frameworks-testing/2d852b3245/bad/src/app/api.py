from fastapi import Depends, FastAPI

app = FastAPI()


@app.get("/livez")
def live(db=Depends(get_db)):
    return {"ok": db.ping()}
