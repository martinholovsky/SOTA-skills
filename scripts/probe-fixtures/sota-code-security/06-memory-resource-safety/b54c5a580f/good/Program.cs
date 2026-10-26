builder.WebHost.ConfigureKestrel(o =>
{
    o.Limits.MinRequestBodyDataRate = new MinDataRate(bytesPerSecond: 240, gracePeriod: TimeSpan.FromSeconds(5));
});
