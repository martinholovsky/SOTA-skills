#include <benchmark/benchmark.h>

int parse(const char*);

static void BM_Parse(benchmark::State& state) {
    for (auto _ : state) benchmark::DoNotOptimize(parse("12345"));
}
BENCHMARK(BM_Parse);
BENCHMARK_MAIN();
