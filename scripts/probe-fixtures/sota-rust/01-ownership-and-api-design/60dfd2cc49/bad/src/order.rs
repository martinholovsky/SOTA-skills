pub struct LineItem {
    pub sku: String,
    pub unit_price: f64,
    pub quantity: u32,
}

pub fn order_total(items: &[LineItem]) -> f64 {
    items.iter().map(|i| i.unit_price * f64::from(i.quantity)).sum()
}
