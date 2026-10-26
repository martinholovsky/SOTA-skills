#include "parser.hpp"

void Parser::reset()
{
    Lexer *lx = new Lexer(input_);
    lexer_ = lx;
}
