#include <memory>
#include "parser.hpp"

void Parser::reset()
{
    lexer_ = std::make_unique<Lexer>(input_);
}
