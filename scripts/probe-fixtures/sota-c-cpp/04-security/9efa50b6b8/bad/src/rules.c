#include <lauxlib.h>
#include <lualib.h>

int run_rule(lua_State *L, const char *body)
{
    luaL_openlibs(L);
    return luaL_dostring(L, body);
}
