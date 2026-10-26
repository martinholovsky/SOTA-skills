def redeem(voucher_id, user):
    # conditional UPDATE closes the check-then-act window atomically
    rows = db.execute("UPDATE vouchers SET redeemed = true WHERE id = %s AND NOT redeemed", (voucher_id,))
    if rows == 0:
        raise AlreadyRedeemed()
