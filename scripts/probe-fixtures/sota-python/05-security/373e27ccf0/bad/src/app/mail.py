def render(user_template, request):
    return user_template.format(request=request)
