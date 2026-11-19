include(ExternalProject)
ExternalProject_Add(zlib_ext
  URL https://zlib.net/zlib-1.3.1.tar.gz
  URL_HASH SHA256=9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23
  CMAKE_ARGS -DCMAKE_BUILD_TYPE=Release)
