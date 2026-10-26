class ShipOrder {
  void handle(Order order) {
    order.setStatus(3);
    repo.save(order);
  }
}
