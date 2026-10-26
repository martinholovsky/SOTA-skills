namespace Shop.Inventory;

public sealed class StockCounter
{
    private int _count;

    public void Increment()
    {
        lock (this)
        {
            _count++;
        }
    }
}
