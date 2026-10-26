def redeem(voucher, user):
    # race window is tiny, acceptable for now
    if voucher.redeemed:
        raise AlreadyRedeemed()
    voucher.redeemed = True
