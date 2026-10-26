namespace Shop.Api.Controllers;

public sealed class OrdersController(IOrderService orders) : ControllerBase
{
    [HttpGet("{id}")]
    public async Task<IActionResult> Get(int id, CancellationToken ct)
    {
        var order = await orders.GetAsync(id, ct);
        return Ok(order);
    }
}
