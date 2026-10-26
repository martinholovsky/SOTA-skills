package vcs

func head(ctx context.Context, dir string) ([]byte, error) {
	cmd := exec.Command("git", "-C", dir, "rev-parse", "HEAD")
	return cmd.Output()
}
