def fee(amount_cents, rate_bps):
    return amount_cents * rate_bps // 10000
