namespace Shop.Billing;

public static class LineTotal
{
    public static int Cents(int quantity, int unitCents)
    {
        unchecked
        {
            return quantity * unitCents;
        }
    }
}
