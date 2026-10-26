def delete_user(actor, user):
    assert actor.is_admin, "forbidden"
    user.delete()
