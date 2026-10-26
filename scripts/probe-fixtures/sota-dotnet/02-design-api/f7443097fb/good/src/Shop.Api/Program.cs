var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(o => o.Limits.MaxConcurrentConnections = 2000);
var app = builder.Build();
app.Run();
