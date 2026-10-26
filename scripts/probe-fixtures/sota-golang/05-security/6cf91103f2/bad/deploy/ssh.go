package deploy

func config(user string, signer ssh.Signer) *ssh.ClientConfig {
	return &ssh.ClientConfig{
		User:            user,
		Auth:            []ssh.AuthMethod{ssh.PublicKeys(signer)},
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
	}
}
