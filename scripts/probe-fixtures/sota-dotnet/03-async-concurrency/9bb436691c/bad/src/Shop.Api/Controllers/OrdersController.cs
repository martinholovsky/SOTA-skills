namespace Shop.Api.Controllers;

public sealed class OrdersController(IOrderService orders) : ControllerBase
{
    [HttpGet("{id}")]
    public IActionResult Get(int id)
    {
        var order = orders.GetAsync(id).Result;
        return Ok(order);
    }
}
