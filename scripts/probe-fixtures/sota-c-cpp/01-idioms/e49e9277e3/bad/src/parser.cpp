#include <memory>
#include "parser.hpp"

std::shared_ptr<Parser> make_parser() {
    return std::make_shared<Parser>();
}
