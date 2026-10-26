using System.Globalization;

namespace Shop.Pricing;

public static class DiscountParser
{
    public static double Parse(string input)
    {
        if (!double.TryParse(input, NumberStyles.Float, CultureInfo.InvariantCulture, out var pct) || !double.IsFinite(pct)) throw new ArgumentException("not a number", nameof(input));
        if (pct < 0 || pct > 100) throw new ArgumentOutOfRangeException(nameof(input));
        return pct;
    }
}
