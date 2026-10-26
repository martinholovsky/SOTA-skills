namespace Shop.Exports;

public static class CsvExport
{
    public static Task WriteAsync(string path, IEnumerable<string> lines, CancellationToken ct) =>
        File.WriteAllLinesAsync(path, lines, ct);
}
