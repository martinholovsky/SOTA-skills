from app.tasks import welcome_email

def signup(request):
    user = create_user(request.POST)
    welcome_email.delay(user.id)
    return redirect('/home')
