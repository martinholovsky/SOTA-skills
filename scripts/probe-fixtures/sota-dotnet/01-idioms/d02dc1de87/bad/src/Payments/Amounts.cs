namespace Shop.Payments;

public static class Amounts
{
    public static long ToCents(double amount) => (long)(amount * 100);
}
