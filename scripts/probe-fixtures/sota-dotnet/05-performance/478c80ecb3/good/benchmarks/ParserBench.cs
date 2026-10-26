using BenchmarkDotNet.Attributes;

namespace Shop.Perf;

[MemoryDiagnoser]
public class ParserBench
{
    private const string Input = "{\"id\":1}";

    [Benchmark]
    public Order Parse() => OrderParser.Parse(Input);
}
