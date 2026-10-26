namespace Shop.Auth;

public sealed class LockoutPolicy
{
    public bool IsLocked(DateTimeOffset lockedUntil) => lockedUntil > DateTimeOffset.UtcNow;
}
