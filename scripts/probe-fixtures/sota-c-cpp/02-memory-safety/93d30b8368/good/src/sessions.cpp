#include <list>

void drop_expired(std::list<Session> &sessions, long now)
{
    for (auto it = sessions.begin(); it != sessions.end();) {
        if (it->expires < now)
            it = sessions.erase(it);
        else
            ++it;
    }
}
