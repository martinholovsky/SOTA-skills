using System.Globalization;

namespace Shop.Pricing;

public static class DiscountParser
{
    public static double Parse(string input)
    {
        var pct = double.Parse(input, CultureInfo.InvariantCulture);
        if (pct < 0 || pct > 100) throw new ArgumentOutOfRangeException(nameof(input));
        return pct;
    }
}
