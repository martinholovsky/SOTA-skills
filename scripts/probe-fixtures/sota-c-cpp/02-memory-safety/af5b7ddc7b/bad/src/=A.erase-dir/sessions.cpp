#include <list>

void drop_expired(std::list<Session> &sessions, long now)
{
    for (auto it = sessions.begin(); it != sessions.end(); ++it) {
        if (it->expires < now)
            sessions.erase(it);
    }
}
