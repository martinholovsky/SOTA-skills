cmake_minimum_required(VERSION 3.24)
project(app CXX)
include(FetchContent)
FetchContent_Declare(json URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
  URL_HASH SHA256=d6c65aca6b1ed68e7a182f4757257b107ae403032760ed6ef121c9d55e81757d)
FetchContent_MakeAvailable(json)
add_executable(app main.cpp)
target_link_libraries(app PRIVATE nlohmann_json::nlohmann_json)
