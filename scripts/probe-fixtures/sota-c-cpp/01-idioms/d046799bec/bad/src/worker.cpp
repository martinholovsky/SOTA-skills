#include "job.hpp"
void run(Job& job) {
    try {
        job.execute();
    } catch (...) {
        job.mark_done();
    }
}
