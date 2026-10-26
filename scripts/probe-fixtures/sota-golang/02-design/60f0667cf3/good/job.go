package job

import "context"

type Job struct {
	id string
}

func Run(ctx context.Context, j Job) error { return nil }

func Process(
	ctx context.Context,
	id string,
) error {
	return nil
}
