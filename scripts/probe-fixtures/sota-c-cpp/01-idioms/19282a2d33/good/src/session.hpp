#pragma once
#include <memory>

class Connection {};

class Session {
public:
    Session();
    ~Session();
    Session(const Session&) = delete;
    Session& operator=(const Session&) = delete;
private:
    std::unique_ptr<Connection> conn_;
};
