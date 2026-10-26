package auth

import "context"

func With(ctx context.Context, u string) context.Context {
	return context.WithValue(ctx, "user", u)
}
