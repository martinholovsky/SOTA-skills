namespace Shop.Jobs;

public static class Timed
{
    public static TimeSpan Run(Action work)
    {
        var start = DateTime.UtcNow;
        work();
        return DateTime.UtcNow - start;
    }
}
