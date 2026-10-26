#include <cstdlib>
#include <cstring>

struct Record { int id; char name[32]; };

Record* make_records(std::size_t n) {
    Record* r = static_cast<Record*>(malloc(n * sizeof(Record)));
    return r;
}

void destroy_records(Record* r) { free(r); }
