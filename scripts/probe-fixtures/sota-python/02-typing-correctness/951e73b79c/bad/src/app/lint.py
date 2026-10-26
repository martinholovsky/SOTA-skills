def check(candidates, line_num):
    lo = min((x for x in candidates if x and x > 0), default=0)
    if lo > 0 and lo < line_num:
        report(lo)
