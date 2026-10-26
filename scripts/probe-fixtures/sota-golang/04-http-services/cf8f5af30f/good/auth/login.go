package auth

func (s *Service) Login(ctx context.Context, user, pass string) error {
	slog.DebugContext(ctx, "login attempt", "user", user)
	return s.check(ctx, user, pass)
}
