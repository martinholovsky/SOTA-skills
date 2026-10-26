#include <cstdio>
#include <string>

std::string load_config(const char* path) {
    FILE* fp = fopen(path, "rb");
    if (!fp) return {};
    std::string out;
    char buf[4096];
    size_t n;
    while ((n = fread(buf, 1, sizeof buf, fp)) > 0) out.append(buf, n);
    fclose(fp);
    return out;
}
