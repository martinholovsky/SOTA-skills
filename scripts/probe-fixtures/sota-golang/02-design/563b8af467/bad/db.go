package db

import (
	"context"
	"time"
)

// Default per-query timeout, skipped whenever the caller already has a deadline:
// under an 8 h job context the query is bounded by 8 h, not 30 s.
func withQueryTimeout(ctx context.Context) (context.Context, context.CancelFunc) {
	if _, ok := ctx.Deadline(); ok {
		return ctx, func() {}
	}
	return context.WithTimeout(ctx, 30*time.Second)
}
