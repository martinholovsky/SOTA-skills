from fastapi import FastAPI
from features import build_row

app = FastAPI()

@app.post('/score')
def score(req: dict):
    return {'y': MODEL.predict([build_row(req)]).tolist()}
