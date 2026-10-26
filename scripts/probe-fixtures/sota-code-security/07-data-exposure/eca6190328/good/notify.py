def notify(user):
    client.messages.create(to=user.phone, from_=SENDER, body="You have a new statement. Sign in to view it.")
