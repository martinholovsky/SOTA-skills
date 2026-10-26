<?php
declare(strict_types=1);

namespace App\Native;

final class Hasher
{
    private \FFI $ffi;

    public function __construct()
    {
        $this->ffi = \FFI::cdef('uint32_t xxh32(const void *p, size_t n, uint32_t seed);', 'libxxhash.so');
    }
}
