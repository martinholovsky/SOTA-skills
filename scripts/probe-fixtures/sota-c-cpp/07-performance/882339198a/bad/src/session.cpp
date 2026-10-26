#include <memory>

struct Session { int id; };

void serve() {
    auto s = std::make_shared<Session>();  // sole owner: shared_ptr not needed
    s->id = 1;
}
std::shared_ptr<Session> g_unused;
