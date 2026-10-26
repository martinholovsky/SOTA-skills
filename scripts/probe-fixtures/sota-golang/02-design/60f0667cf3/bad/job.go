package job

import "context"

type Job struct {
	ctx context.Context
	id  string
}
