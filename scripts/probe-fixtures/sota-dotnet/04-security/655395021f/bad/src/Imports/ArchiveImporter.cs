using System.IO.Compression;

namespace Shop.Imports;

public static class ArchiveImporter
{
    public static void Extract(ZipArchive zip, string destination)
    {
        foreach (var entry in zip.Entries)
            entry.ExtractToFile(Path.Combine(destination, entry.FullName), overwrite: true);
    }
}
