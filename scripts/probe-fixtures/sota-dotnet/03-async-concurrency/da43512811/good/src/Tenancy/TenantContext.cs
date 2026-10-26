namespace Shop.Tenancy;

public sealed class TenantContext
{
    public string? TenantId { get; set; }
}

public static class TenantRegistration
{
    public static IServiceCollection AddTenantContext(this IServiceCollection services) => services.AddScoped<TenantContext>();
}
