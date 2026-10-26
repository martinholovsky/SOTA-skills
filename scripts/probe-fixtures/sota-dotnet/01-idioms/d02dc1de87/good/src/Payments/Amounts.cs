namespace Shop.Payments;

public static class Amounts
{
    public static long ToCents(decimal amount) => (long)Math.Round(amount * 100m, MidpointRounding.AwayFromZero);
}
