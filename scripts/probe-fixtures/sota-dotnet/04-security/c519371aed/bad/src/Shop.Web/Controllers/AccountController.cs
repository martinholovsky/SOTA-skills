namespace Shop.Web.Controllers;

public sealed class AccountController : Controller
{
    [HttpPost]
    public IActionResult LoginDone(string returnUrl) => Redirect(returnUrl);
}
