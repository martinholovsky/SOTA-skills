override CFLAGS += -O2 -D_FORTIFY_SOURCE=3 -fstack-protector-strong
override LDFLAGS += -Wl,-z,relro,-z,now

app: main.o
	$(CC) $(LDFLAGS) -o $@ $^
