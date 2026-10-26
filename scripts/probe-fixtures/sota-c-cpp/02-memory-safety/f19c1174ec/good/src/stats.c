struct stats { long hits; long misses; };

struct stats snapshot(void)
{
    struct stats s = { 0, 0 };
    s.hits = read_hits();
    return s;
}
