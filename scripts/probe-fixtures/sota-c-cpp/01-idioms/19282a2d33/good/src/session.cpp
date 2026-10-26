#include "session.hpp"
#include <memory>

Session::Session() : conn_(std::make_unique<Connection>()) {}

Session::~Session() = default;
