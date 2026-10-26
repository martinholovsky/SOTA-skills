public sealed class UserService
{
    public async Task<User> GetUserAsync(string id, CancellationToken ct)
    {
        return await _repo.FindAsync(id, ct);
    }
}
