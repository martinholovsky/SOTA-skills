var builder = WebApplication.CreateBuilder(args);
builder.Services.AddAuthorization();
var app = builder.Build();
app.Run();
