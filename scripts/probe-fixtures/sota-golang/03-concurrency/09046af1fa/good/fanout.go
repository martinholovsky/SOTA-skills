package fanout

func run(jobs []Job) {
	var wg sync.WaitGroup
	for _, j := range jobs {
		wg.Add(1)
		go func() {
			defer wg.Done()
			j.Do()
		}()
	}
	wg.Wait()
}
