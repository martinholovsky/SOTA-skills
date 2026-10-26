namespace Shop.Import;

public sealed class CsvImporter(ILogger<CsvImporter> log)
{
    public void Import(string path)
    {
        try
        {
            File.ReadAllLines(path);
        }
        catch (IOException ex)
        {
            log.LogError(ex, "import failed");
            throw ex;
        }
    }
}
