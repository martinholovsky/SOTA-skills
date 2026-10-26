#include <string>

struct RequestCtx { std::string tenant_id; };

void handle(const RequestCtx& rc);
