def award(referrer, new_user):
    if same_person(referrer, new_user):  # device, payment instrument, verified phone
        return
    credit(referrer, REWARD)
