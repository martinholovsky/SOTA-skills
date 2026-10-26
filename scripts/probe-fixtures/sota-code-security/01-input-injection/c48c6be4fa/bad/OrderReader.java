public Order read(InputStream raw) throws Exception {
    ObjectInputStream in = new ObjectInputStream(raw);
    Order order = (Order) in.readObject();
    return order;
}
