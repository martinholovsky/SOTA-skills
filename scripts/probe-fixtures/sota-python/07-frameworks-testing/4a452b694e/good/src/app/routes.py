from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/rate")
async def rate(request: Request):
    return (await request.app.state.http.get("https://fx.example/rate")).json()
