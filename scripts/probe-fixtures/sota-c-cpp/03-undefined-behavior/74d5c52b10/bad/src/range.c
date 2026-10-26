int in_bounds(int off, int len, int size)
{
    if (off + len < off)
        return 0;
    return off + len <= size;
}
