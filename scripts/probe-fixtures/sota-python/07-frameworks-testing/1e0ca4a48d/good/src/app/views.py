def search(request):
    q = request.GET["q"]
    return Book.objects.filter(title=q)
