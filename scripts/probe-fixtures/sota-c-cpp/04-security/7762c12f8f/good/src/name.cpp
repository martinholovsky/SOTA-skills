#include <regex>
#include <string>

bool valid_name(const std::string& s)
{
    static const std::regex kName{R"([a-z][a-z0-9_]{0,31})"};
    return s.size() <= 32 && std::regex_match(s, kName);
}
