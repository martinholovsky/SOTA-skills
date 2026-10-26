namespace Shop.Data;

public static class OrderSearch
{
    public static string Sql(string sort) => sort switch
    {
        "total" => "SELECT Id, Total FROM Orders ORDER BY Total",
        _ => "SELECT Id, Total FROM Orders ORDER BY Id",
    };
}
