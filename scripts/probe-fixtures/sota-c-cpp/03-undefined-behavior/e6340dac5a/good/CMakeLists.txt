project(svc CXX)
add_executable(svc main.cpp)
target_compile_options(svc PRIVATE -fcontract-evaluation-semantic=enforce)
