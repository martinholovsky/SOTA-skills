import sys

sys.setrecursionlimit(100_000)


def depth(node):
    return 1 + max((depth(c) for c in node.children), default=0)
