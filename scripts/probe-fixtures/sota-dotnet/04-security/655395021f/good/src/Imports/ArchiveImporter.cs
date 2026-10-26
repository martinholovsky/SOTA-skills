using System.IO.Compression;

namespace Shop.Imports;

public static class ArchiveImporter
{
    public static void Extract(string zipPath, string destination)
    {
        ZipFile.ExtractToDirectory(zipPath, destination, overwriteFiles: true);
    }
}
