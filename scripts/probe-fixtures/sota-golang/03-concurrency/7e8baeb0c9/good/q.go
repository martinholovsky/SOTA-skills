package q

type Job struct{}

var jobs = make(chan Job, 100) // absorbs the measured p99 burst of 80; producers block beyond it
