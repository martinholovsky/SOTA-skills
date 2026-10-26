#include <vector>

struct Record { int id; char name[32]; };

std::vector<Record> make_records(std::size_t n) {
    return std::vector<Record>(n);
}
