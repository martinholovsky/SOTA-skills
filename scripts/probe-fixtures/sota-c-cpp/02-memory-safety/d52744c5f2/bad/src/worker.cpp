#include <thread>
#include <vector>

void start_upload(std::vector<char> buf)
{
    std::thread t([&] { upload(buf); });
    t.detach();
}
