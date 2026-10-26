def search(request):
    q = request.GET["q"]
    return Book.objects.raw(f"SELECT * FROM book WHERE title = '{q}'")
