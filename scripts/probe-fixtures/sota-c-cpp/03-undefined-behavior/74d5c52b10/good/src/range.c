int in_bounds(int off, int len, int size)
{
    int end;
    if (__builtin_add_overflow(off, len, &end))
        return 0;
    return end <= size;
}
