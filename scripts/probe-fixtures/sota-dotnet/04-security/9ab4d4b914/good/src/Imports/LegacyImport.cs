using System.Text.Json;

namespace Shop.Imports;

public static class LegacyImport
{
    public static ImportBatch? Read(Stream upload) => JsonSerializer.Deserialize<ImportBatch>(upload, JsonSerializerOptions.Strict);
}
