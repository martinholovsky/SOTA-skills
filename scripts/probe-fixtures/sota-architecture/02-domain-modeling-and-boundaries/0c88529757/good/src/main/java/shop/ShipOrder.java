class ShipOrder {
  void handle(Order order) {
    order.markShipped();
    repo.save(order);
  }
}
