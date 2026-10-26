using System.Text;

namespace Shop.Exports;

public static class CsvLine
{
    public static string Build(IEnumerable<Item> items)
    {
        var csv = new StringBuilder();
        foreach (var item in items)
        {
            csv.Append(item.Name).Append(',');
        }
        return csv.ToString();
    }
}
