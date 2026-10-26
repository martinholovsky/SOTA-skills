package fanout

func run(jobs []Job) {
	var wg sync.WaitGroup
	for _, j := range jobs {
		go func() {
			wg.Add(1)
			defer wg.Done()
			j.Do()
		}()
	}
	wg.Wait()
}
