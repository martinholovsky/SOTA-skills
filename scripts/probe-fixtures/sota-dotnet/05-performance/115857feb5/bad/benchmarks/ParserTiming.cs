using System.Diagnostics;

namespace Shop.Perf;

public static class ParserTiming
{
    public static TimeSpan Measure(string input)
    {
        var sw = Stopwatch.StartNew();
        for (var i = 0; i < 10_000; i++) OrderParser.Parse(input);
        return sw.Elapsed;
    }
}
