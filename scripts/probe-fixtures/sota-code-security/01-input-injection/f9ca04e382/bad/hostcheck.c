int allowed(const char *host) {
    struct in_addr addr;
    if (inet_aton(host, &addr) == 0) return 0;
    return !is_internal(addr);
}
