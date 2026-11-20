namespace Shop.Billing;

public static class Tax
{
    public static decimal Vat(decimal net) => Math.Round(net * 0.21m, 2);
}
