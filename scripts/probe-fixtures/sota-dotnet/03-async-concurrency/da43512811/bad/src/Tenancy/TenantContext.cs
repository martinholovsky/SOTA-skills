namespace Shop.Tenancy;

public static class TenantContext
{
    [ThreadStatic]
    private static string? _tenantId;

    public static string? TenantId { get => _tenantId; set => _tenantId = value; }
}
