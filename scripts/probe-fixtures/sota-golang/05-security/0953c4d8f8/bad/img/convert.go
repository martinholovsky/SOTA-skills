package img

func Convert(name string) error {
	return exec.Command("convert", name, "out.png").Run()
}
