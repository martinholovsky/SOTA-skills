using System.Diagnostics;

namespace Shop.Perf;

public static class ParserBench
{
    public static TimeSpan Run(string input)
    {
        var sw = Stopwatch.StartNew();
        for (var i = 0; i < 10_000; i++) OrderParser.Parse(input);
        return sw.Elapsed;
    }
}
