namespace Shop.Reports;

public static class Overdue
{
    public static string Summary(IEnumerable<Invoice> invoices, DateOnly today)
    {
        var overdue = invoices.Where(i => i.DueDate < today);
        return $"{overdue.Count()} overdue, oldest {overdue.Min(i => i.DueDate)}";
    }
}
