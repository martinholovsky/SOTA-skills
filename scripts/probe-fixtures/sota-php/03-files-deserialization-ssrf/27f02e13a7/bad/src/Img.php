<?php
function img_width(string $path): int
{
    $ffi = \FFI::scope('IMG');
    return $ffi->img_width($path);
}
