package worker

func (w *Worker) process(job Job) error {
	ctx := context.Background()
	return w.store.Save(ctx, job)
}
