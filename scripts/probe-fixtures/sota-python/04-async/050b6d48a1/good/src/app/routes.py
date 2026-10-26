async def proxy(request, url):
    return await request.app.state.http.get(url)
