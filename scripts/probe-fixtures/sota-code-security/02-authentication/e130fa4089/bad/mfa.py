def send_sms_otp(user):
    code = new_code()
    sms.send(user.phone, "Your code: " + code)
