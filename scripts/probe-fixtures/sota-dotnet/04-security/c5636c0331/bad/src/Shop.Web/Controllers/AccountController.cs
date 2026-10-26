namespace Shop.Web.Controllers;

public sealed class AccountController(IAccountService accounts) : Controller
{
    [Route("account/delete")]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> Delete()
    {
        await accounts.DeleteAsync(User);
        return RedirectToAction("Index", "Home");
    }
}
