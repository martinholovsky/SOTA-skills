namespace Shop.Admin;

public enum Role { User, Admin }

public static class RoleEndpoint
{
    public static Role ReadRole(HttpRequest request)
    {
        var role = (Role)int.Parse(request.Query["role"]!);
        return role;
    }
}
