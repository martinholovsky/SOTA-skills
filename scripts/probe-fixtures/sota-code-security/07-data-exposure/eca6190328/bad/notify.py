def notify(user):
    client.messages.create(to=user.phone, from_=SENDER, body=f"Your balance is {user.balance}")
