#include <string>
#include <string_view>

std::string_view display_name(const User &u)
{
    std::string full = u.first + " " + u.last;
    return std::string_view(full);
}
