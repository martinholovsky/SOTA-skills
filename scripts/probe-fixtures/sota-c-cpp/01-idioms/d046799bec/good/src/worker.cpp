#include "job.hpp"
#include "log.hpp"
void run(Job& job) {
    try {
        job.execute();
    } catch (...) {
        log_error("job failed; rethrowing");
        throw;
    }
}
