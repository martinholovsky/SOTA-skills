namespace Shop.Files;

public static class DownloadEndpoint
{
    private const string Root = "/srv/shop/files/";

    public static IResult Get(string name)
    {
        var full = Path.GetFullPath(Path.Join(Root, Path.GetFileName(name)));
        return full.StartsWith(Root, StringComparison.Ordinal) ? Results.File(full) : Results.NotFound();
    }
}
