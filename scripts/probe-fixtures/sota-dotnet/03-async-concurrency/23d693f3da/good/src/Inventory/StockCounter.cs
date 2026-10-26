namespace Shop.Inventory;

public sealed class StockCounter
{
    private readonly Lock _gate = new();
    private int _count;

    public void Increment()
    {
        lock (_gate)
        {
            _count++;
        }
    }
}
