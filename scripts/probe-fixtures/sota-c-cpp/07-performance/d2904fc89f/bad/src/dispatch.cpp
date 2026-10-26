int handle(int op) {
    if (op == 0) [[likely]] {
        return 1;
    }
    return 0;
}
