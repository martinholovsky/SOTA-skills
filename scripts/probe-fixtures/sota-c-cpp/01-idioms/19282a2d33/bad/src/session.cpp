#include "session.hpp"

Session::Session() : conn_(new Connection()) {}

Session::~Session() {
    delete conn_;
}
