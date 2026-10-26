def depth(root):
    best, stack = 0, [(root, 1)]
    while stack:
        node, d = stack.pop()
        best = max(best, d)
        stack.extend((c, d + 1) for c in node.children)
    return best
