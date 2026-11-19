package db

type QueryError struct {
	Query string
	Err   error
}

func (e *QueryError) Error() string { return "query " + e.Query + ": " + e.Err.Error() }

func (e *QueryError) Unwrap() error { return e.Err }
