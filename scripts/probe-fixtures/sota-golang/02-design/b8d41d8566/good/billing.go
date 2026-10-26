package billing

func (s *Service) Charge(ctx context.Context, inv Invoice) error {
	return s.gateway.Charge(ctx, inv)
}
