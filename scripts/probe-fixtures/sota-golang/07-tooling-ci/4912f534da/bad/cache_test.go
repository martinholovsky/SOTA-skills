package cache

func TestExpiry(t *testing.T) {
	c := New(10 * time.Millisecond)
	c.Set("k", 1)
	time.Sleep(20 * time.Millisecond)
	if _, ok := c.Get("k"); ok {
		t.Fatal("not expired")
	}
}
