package auth

func (s *Service) Login(ctx context.Context, user, password string) error {
	slog.DebugContext(ctx, "login attempt", "user", user, "password", password)
	return s.check(ctx, user, password)
}
