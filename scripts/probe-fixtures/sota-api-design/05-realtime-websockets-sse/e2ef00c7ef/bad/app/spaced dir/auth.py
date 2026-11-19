def logout(request):
    request.session.flush()
    return redirect('/login')
