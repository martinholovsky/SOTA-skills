package consumer

func (c *Consumer) loop(ch <-chan Msg) {
	t := time.NewTimer(c.idle)
	defer t.Stop()
	for {
		select {
		case m := <-ch:
			c.handle(m)
		case <-t.C:
			c.flush()
		}
		t.Reset(c.idle)
	}
}
