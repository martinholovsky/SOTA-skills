public sealed class Secret { public override string ToString() => "[REDACTED]"; }
public record Creds
{
    public required string User { get; init; }
    public required Secret Password { get; init; }
}
