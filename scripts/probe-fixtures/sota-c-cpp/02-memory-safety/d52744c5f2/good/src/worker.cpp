#include <thread>
#include <vector>

void start_upload(std::vector<char> buf)
{
    std::thread t([buf = std::move(buf)] { upload(buf); });
    t.detach();
}
