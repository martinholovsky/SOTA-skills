package billing

func (s *Service) Charge(inv Invoice) error {
	return s.gateway.Charge(context.TODO(), inv)
}
