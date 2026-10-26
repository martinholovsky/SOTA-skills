volatile bool done_flag = false;

void worker() {
    while (!done_flag) { /* spin */ }
}
