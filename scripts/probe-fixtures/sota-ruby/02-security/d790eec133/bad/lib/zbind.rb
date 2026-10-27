require "ffi"

module ZBind
  extend FFI::Library
  ffi_lib "z"
  attach_function :crc32, [:ulong, :pointer, :uint], :ulong
end
