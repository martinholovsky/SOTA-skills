from django.core.mail import send_mail

def signup(request):
    user = create_user(request.POST)
    send_mail('Welcome', render_welcome(user), 'no-reply@example.com', [user.email])
    return redirect('/home')
