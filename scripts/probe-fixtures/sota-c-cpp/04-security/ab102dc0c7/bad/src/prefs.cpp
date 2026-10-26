#include <drogon/drogon.h>

void set_theme(const drogon::HttpResponsePtr& resp, const std::string& theme)
{
    resp->addCookie("theme", theme);
}
