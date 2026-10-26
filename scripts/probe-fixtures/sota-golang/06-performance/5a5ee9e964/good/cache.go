package cache

func (c *Cache) Get(k string) (v []byte, ok bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	v, ok = c.m[k]
	return v, ok
}
