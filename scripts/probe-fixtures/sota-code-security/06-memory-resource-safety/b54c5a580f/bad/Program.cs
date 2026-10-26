builder.WebHost.ConfigureKestrel(o =>
{
    o.Limits.MinRequestBodyDataRate = null;
});
