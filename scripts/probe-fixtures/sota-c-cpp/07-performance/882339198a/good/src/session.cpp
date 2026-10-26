#include <memory>

struct Session { int id; };

void serve() {
    auto s = std::make_unique<Session>();
    s->id = 1;
}
