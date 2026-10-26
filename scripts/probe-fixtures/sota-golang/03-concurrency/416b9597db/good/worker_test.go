package worker

func TestWorkerProcesses(t *testing.T) {
	w := Start()
	done := w.Submit(job)
	select {
	case <-done:
	case <-t.Context().Done():
		t.Fatal("job not processed")
	}
}
