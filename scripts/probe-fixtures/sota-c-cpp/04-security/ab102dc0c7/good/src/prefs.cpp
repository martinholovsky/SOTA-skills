#include <drogon/drogon.h>

void set_theme(const drogon::HttpResponsePtr& resp, const std::string& theme)
{
    drogon::Cookie c("__Host-theme", theme);
    c.setSecure(true);
    c.setHttpOnly(true);
    c.setSameSite(drogon::Cookie::SameSite::kLax);
    c.setPath("/");
    resp->addCookie(c);
}
