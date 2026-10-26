package img

func Convert(ctx context.Context, name string) error {
	cmd := exec.CommandContext(ctx, "convert", "--", name, "out.png")
	cmd.Env = []string{"PATH=/usr/bin"}
	cmd.WaitDelay = 5 * time.Second
	return cmd.Run()
}
