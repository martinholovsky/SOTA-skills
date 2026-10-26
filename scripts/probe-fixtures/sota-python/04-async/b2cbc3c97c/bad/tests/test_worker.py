async def test_worker_runs():
    assert await run_once() == 1
