public Order read(InputStream raw) throws Exception {
    ObjectInputStream in = new ObjectInputStream(raw);
    in.setObjectInputFilter(ObjectInputFilter.Config.createFilter("com.example.Order;!*"));
    Object obj = in.readObject();
    return (Order) obj;
}
