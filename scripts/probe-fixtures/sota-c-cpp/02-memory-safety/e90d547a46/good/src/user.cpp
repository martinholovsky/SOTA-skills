#include <string>

std::string display_name(const User &u)
{
    std::string full = u.first + " " + u.last;
    return full;
}
