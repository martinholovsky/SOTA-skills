namespace Shop.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public sealed class OrdersController : ControllerBase
{
    [HttpGet("{id}")]
    public IActionResult Get(int id) => Ok(id);
}
