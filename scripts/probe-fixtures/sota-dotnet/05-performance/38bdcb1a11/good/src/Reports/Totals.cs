namespace Shop.Reports;

public static class Totals
{
    public static List<int> Collect(IEnumerable<int> values) => new(values);
}
