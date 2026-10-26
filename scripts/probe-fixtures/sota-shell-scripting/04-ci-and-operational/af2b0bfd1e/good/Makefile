lint:
	for f in scripts/*.sh; do shellcheck "$$f"; done
build:
	$(CC) -o app main.c ${LDFLAGS}
