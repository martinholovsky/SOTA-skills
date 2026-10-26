#pragma once

namespace net {
int connect_to(const char* host, int port = 8080, int timeout_ms = 5000);
}
