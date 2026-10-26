var builder = WebApplication.CreateBuilder(args);
builder.Services.AddDataProtection();
var app = builder.Build();
app.Run();
