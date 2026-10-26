public class Cache {
  private final Object lock = new Object();
  private final Map<String, String> m = new HashMap<>();
  public void put(String k, String v) { synchronized (lock) { m.put(k, v); } }
}
