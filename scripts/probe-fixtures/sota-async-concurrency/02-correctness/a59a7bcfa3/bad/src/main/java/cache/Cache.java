public class Cache {
  private final Map<String, String> m = new HashMap<>();
  public synchronized void put(String k, String v) { m.put(k, v); }
}
