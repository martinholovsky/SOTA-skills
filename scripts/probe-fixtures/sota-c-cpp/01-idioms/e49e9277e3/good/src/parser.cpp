#include <memory>
#include "parser.hpp"

std::unique_ptr<Parser> make_parser() {
    return std::make_unique<Parser>();
}
