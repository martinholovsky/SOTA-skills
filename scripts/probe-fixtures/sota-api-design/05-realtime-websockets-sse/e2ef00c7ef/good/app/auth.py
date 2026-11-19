from app.realtime import registry

def logout(request):
    sid = request.session.session_key
    request.session.flush()
    registry.close_connections_for_session(sid)
    return redirect('/login')
