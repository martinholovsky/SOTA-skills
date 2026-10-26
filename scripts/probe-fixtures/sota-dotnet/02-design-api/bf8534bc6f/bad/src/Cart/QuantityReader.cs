namespace Shop.Cart;

public static class QuantityReader
{
    public static int Read(string input)
    {
        int.TryParse(input, out var qty);
        return qty;
    }
}
