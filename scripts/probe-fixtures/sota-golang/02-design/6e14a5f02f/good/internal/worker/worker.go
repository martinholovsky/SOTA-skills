package worker

func (w *Worker) process(ctx context.Context, job Job) error {
	return w.store.Save(ctx, job)
}
