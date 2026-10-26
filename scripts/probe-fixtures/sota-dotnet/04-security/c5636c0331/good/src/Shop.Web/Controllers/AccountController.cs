namespace Shop.Web.Controllers;

public sealed class AccountController(IAccountService accounts) : Controller
{
    [HttpPost("account/delete")]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> Delete()
    {
        await accounts.DeleteAsync(User);
        return RedirectToAction("Index", "Home");
    }
}
