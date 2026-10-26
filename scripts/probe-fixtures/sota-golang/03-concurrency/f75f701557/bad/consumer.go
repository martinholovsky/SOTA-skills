package consumer

func (c *Consumer) loop(ch <-chan Msg) {
	for {
		select {
		case m := <-ch:
			c.handle(m)
		case <-time.After(c.idle):
			c.flush()
		}
	}
}
