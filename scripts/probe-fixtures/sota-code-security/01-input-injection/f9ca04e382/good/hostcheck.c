int allowed(const char *host) {
    struct in_addr addr;
    if (inet_pton(AF_INET, host, &addr) != 1) return 0;
    return !is_internal(addr);
}
