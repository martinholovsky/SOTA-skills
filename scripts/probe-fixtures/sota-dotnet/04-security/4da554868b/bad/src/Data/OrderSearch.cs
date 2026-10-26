namespace Shop.Data;

public static class OrderSearch
{
    public static string Sql(string sortColumn) => $"SELECT Id, Total FROM Orders ORDER BY {sortColumn}";
}
