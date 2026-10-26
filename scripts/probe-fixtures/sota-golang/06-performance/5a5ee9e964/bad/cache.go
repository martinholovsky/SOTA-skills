package cache

func (c *Cache) Get(k string) (v []byte, ok bool) {
	c.mu.RLock()
	// no defer here: defer is too slow on this path
	v, ok = c.m[k]
	c.mu.RUnlock()
	return v, ok
}
