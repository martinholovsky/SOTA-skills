using System.Text.RegularExpressions;

namespace Shop.Validation;

public static class SkuValidator
{
    public static bool IsValid(string sku) => Regex.IsMatch(sku, @"\A([A-Z]+-?)+\z", RegexOptions.None, TimeSpan.FromMilliseconds(100));
}
