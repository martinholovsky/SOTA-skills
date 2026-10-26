using System.Diagnostics;

namespace Shop.Images;

public static class Thumbnailer
{
    public static void Make(string upload) =>
        Process.Start("/bin/sh", $"-c \"convert {upload} -resize 200x200 thumb.png\"");
}
