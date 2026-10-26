package deploy

func config(user string, signer ssh.Signer) (*ssh.ClientConfig, error) {
	hk, err := knownhosts.New("/etc/ssh/ssh_known_hosts")
	if err != nil {
		return nil, err
	}
	return &ssh.ClientConfig{
		User:            user,
		Auth:            []ssh.AuthMethod{ssh.PublicKeys(signer)},
		HostKeyCallback: hk,
	}, nil
}
