namespace Shop.Catalog;

public sealed class SkuIndex(IReadOnlyList<string> skus)
{
    public int Find(string sku)
    {
        for (var i = 0; i < skus.Count; i++)
            if (skus[i] == sku) return i;
        return -1;
    }
}
