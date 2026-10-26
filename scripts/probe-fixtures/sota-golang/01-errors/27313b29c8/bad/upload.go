package upload

func finish(tmp string) {
	_ = os.Remove(tmp)
}
