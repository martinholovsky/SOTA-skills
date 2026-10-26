def delete_user(actor, user):
    if not actor.is_admin:
        raise PermissionError("forbidden")
    user.delete()
