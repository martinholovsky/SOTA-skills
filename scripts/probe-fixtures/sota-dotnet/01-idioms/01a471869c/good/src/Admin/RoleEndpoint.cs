namespace Shop.Admin;

public enum Role { User, Admin }

public static class RoleEndpoint
{
    public static Role ReadRole(HttpRequest request) => request.Query["role"].ToString() switch
    {
        "user" => Role.User,
        "admin" => Role.Admin,
        _ => throw new BadHttpRequestException("unknown role"),
    };
}
