package cache

func TestExpiry(t *testing.T) {
	clk := &fakeClock{}
	c := New(10*time.Millisecond, clk)
	c.Set("k", 1)
	clk.Advance(20 * time.Millisecond)
	if _, ok := c.Get("k"); ok {
		t.Fatal("not expired")
	}
}
