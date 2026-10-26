var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(o =>
{
    o.Limits.MaxRequestBodySize = 10 * 1024 * 1024;
});
var app = builder.Build();
app.Run();
