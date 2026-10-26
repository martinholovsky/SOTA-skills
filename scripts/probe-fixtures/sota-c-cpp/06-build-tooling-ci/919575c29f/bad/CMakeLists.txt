include(ExternalProject)
ExternalProject_Add(zlib_ext
  URL https://zlib.net/zlib-1.3.1.tar.gz
  CMAKE_ARGS -DCMAKE_BUILD_TYPE=Release)
