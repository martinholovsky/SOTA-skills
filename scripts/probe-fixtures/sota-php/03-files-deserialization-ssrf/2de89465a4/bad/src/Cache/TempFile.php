<?php
final class TempFile
{
    public function __construct(private string $path) {}

    public function __destruct()
    {
        @unlink($this->path);
    }
}
