def check(candidates, line_num):
    lo = min((x for x in candidates if x is not None), default=None)
    if lo is not None and line_num is not None and lo < line_num:
        report(lo)
