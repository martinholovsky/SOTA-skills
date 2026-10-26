namespace Shop.Files;

public static class DownloadEndpoint
{
    private const string Root = "/srv/shop/files";

    public static IResult Get(string name) => Results.File(Path.Combine(Root, name));
}
