use rust_decimal::Decimal;

pub struct LineItem {
    pub sku: String,
    pub unit_price: Decimal,
    pub quantity: u32,
}

pub fn order_total(items: &[LineItem]) -> Decimal {
    items.iter().map(|i| i.unit_price * Decimal::from(i.quantity)).sum()
}
