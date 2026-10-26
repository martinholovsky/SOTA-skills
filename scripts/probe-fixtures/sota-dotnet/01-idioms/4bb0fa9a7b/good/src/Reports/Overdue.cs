namespace Shop.Reports;

public static class Overdue
{
    public static string Summary(IReadOnlyList<Invoice> invoices, DateOnly today)
    {
        var count = 0;
        var oldest = DateOnly.MaxValue;
        foreach (var i in invoices)
        {
            if (i.DueDate >= today) continue;
            count++;
            if (i.DueDate < oldest) oldest = i.DueDate;
        }
        return $"{count} overdue, oldest {oldest}";
    }
}
