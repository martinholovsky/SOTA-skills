var builder = WebApplication.CreateBuilder(args);
builder.Services.AddAuthorization(o => o.FallbackPolicy = new AuthorizationPolicyBuilder().RequireAuthenticatedUser().Build());
var app = builder.Build();
app.Run();
