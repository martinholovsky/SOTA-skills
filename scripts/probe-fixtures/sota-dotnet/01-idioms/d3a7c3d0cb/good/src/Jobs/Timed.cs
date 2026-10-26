using System.Diagnostics;

namespace Shop.Jobs;

public static class Timed
{
    public static TimeSpan Run(Action work)
    {
        var sw = Stopwatch.StartNew();
        work();
        return sw.Elapsed;
    }
}
