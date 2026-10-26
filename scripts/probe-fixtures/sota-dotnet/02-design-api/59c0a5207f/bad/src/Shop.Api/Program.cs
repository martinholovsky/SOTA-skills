var builder = WebApplication.CreateBuilder(args);
builder.WebHost.ConfigureKestrel(o =>
{
    o.Limits.MaxRequestBodySize = null;
});
var app = builder.Build();
app.Run();
