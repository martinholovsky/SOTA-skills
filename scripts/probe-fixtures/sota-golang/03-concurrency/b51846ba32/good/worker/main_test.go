package worker

func TestMain(m *testing.M) {
	goleak.VerifyTestMain(m)
}
