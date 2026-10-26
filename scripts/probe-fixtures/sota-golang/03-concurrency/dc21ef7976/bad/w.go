package w

import "context"

func Watch(ctx context.Context, ch chan int) {
	go func() {
		select {
		case <-ctx.Done():
		}
	}()
}

func Drain(ch chan int) {
	go func() {
		for m := range ch {
			_ = m
		}
	}()
}
