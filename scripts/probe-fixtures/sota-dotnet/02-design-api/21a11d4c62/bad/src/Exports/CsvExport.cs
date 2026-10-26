namespace Shop.Exports;

public static class CsvExport
{
    public static void Write(string path, IEnumerable<string> lines)
    {
        var writer = new StreamWriter(path);
        foreach (var line in lines) writer.WriteLine(line);
    }
}
