using System.Collections;

namespace Shop.Reports;

public static class Totals
{
    public static ArrayList Collect(IEnumerable<int> values)
    {
        var list = new ArrayList();
        foreach (var v in values) list.Add(v);
        return list;
    }
}
