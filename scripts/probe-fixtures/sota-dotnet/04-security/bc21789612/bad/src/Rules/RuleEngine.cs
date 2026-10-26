using Microsoft.CodeAnalysis.CSharp.Scripting;

namespace Shop.Rules;

public static class RuleEngine
{
    public static Task<bool> EvaluateAsync(string expression, Order order) =>
        CSharpScript.EvaluateAsync<bool>(expression, globals: order);
}
