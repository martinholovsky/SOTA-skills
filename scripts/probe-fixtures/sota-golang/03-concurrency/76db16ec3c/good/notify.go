package notify

func (s *Service) OnSignup(ctx context.Context, u User) error {
	g, ctx := errgroup.WithContext(ctx)
	g.Go(func() error { return s.mailer.SendWelcome(ctx, u) })
	return g.Wait()
}
