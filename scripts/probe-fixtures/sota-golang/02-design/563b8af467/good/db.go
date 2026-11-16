package db

import (
	"context"
	"time"
)

// WithTimeout keeps the parent's deadline when it is sooner: min(30s, remaining).
func withQueryTimeout(ctx context.Context) (context.Context, context.CancelFunc) {
	return context.WithTimeout(ctx, 30*time.Second)
}

// Reading the deadline for logging is not the anti-pattern.
func remaining(ctx context.Context) time.Duration {
	if dl, ok := ctx.Deadline(); ok {
		return time.Until(dl)
	}
	return -1
}
