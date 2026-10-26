namespace Shop.Auth;

public sealed class LockoutPolicy(TimeProvider time)
{
    public bool IsLocked(DateTimeOffset lockedUntil) => lockedUntil > time.GetUtcNow();
}
