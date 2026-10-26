import requests
from fastapi import APIRouter

router = APIRouter()


@router.get("/rate")
async def rate():
    return requests.get("https://fx.example/rate", timeout=5).json()
