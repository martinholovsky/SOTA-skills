var builder = WebApplication.CreateBuilder(args);
builder.Services.AddDataProtection().PersistKeysToAzureBlobStorage(new Uri(builder.Configuration["Keys:BlobUri"]!), new DefaultAzureCredential()).ProtectKeysWithAzureKeyVault(new Uri(builder.Configuration["Keys:KeyId"]!), new DefaultAzureCredential());
var app = builder.Build();
app.Run();
