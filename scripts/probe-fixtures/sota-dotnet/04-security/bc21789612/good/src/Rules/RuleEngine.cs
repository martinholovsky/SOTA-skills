namespace Shop.Rules;

public static class RuleEngine
{
    private static readonly Dictionary<string, Func<Order, bool>> Rules = new(StringComparer.Ordinal)
    {
        ["free-shipping"] = o => o.Total >= 50m,
        ["vip"] = o => o.Customer.IsVip,
    };

    public static bool Evaluate(string ruleName, Order order) =>
        Rules.TryGetValue(ruleName, out var rule) ? rule(order) : throw new ArgumentException("unknown rule", nameof(ruleName));
}
