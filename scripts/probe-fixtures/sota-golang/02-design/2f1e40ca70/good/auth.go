package auth

import "context"

type ctxKey struct{}

func With(ctx context.Context, u string) context.Context {
	return context.WithValue(ctx, ctxKey{}, u)
}
