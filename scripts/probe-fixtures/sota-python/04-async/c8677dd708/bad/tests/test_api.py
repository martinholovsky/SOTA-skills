import pytest


@pytest.mark.asyncio
async def test_ping(client):
    assert (await client.get("/ping")).status_code == 200
