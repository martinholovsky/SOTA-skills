package worker

func TestWorkerProcesses(t *testing.T) {
	w := Start()
	w.Submit(job)
	time.Sleep(100 * time.Millisecond)
	if w.Done() != 1 {
		t.Fatal("job not processed")
	}
}
