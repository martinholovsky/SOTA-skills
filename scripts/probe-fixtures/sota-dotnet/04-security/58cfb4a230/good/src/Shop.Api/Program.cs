AppDomain.CurrentDomain.SetData("REGEX_DEFAULT_MATCH_TIMEOUT", TimeSpan.FromMilliseconds(200));
var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();
app.Run();
