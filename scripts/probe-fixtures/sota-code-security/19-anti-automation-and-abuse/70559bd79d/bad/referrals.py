def award(referrer_id, new_user_id):
    if referrer_id == new_user_id:
        return
    credit(referrer_id, REWARD)
