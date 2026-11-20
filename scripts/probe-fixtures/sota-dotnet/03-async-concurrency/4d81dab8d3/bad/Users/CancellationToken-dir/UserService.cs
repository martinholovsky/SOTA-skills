public sealed class UserService
{
    public async Task<User> GetUserAsync(string id)
    {
        return await _repo.FindAsync(id);
    }
}
