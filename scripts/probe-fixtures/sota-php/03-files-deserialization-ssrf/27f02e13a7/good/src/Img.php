<?php
function img_width(string $path): int
{
    $size = getimagesize($path);
    return $size === false ? 0 : $size[0];
}
