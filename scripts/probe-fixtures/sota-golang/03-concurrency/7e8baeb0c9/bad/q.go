package q

type Job struct{}

var jobs = make(chan Job, 100)
