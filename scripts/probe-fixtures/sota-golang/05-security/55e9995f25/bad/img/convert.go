package img

func Convert(ctx context.Context, name string) error {
	return exec.CommandContext(ctx, "sh", "-c", "convert "+name+" out.png").Run()
}
