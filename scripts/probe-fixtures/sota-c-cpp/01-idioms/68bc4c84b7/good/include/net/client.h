#pragma once

namespace net {
int connect_to(const char* host, int port, int timeout_ms);
int connect_to(const char* host);
}
