package w

import "context"

func Watch(ctx context.Context, ch chan int) {
	go func() {
		select {
		case <-ctx.Done():
		}
	}()
}
