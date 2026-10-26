package notify

func (s *Service) OnSignup(u User) {
	go func() {
		s.mailer.SendWelcome(u)
	}()
}
