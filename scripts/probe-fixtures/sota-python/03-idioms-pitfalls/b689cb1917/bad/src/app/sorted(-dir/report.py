from itertools import groupby


def by_day(events):
    return {k: list(g) for k, g in groupby(events, key=day)}
