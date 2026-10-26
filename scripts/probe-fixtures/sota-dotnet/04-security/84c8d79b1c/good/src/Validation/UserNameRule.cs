using System.Text.RegularExpressions;

namespace Shop.Validation;

public static class UserNameRule
{
    private static readonly Regex Pattern = new(@"\A[a-z0-9_]{3,20}\z", RegexOptions.None, TimeSpan.FromMilliseconds(50));

    public static bool IsValid(string name) => Pattern.IsMatch(name);
}
