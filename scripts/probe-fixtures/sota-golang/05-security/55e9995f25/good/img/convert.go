package img

func Convert(ctx context.Context, name string) error {
	return exec.CommandContext(ctx, "convert", "--", name, "out.png").Run()
}
