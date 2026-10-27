<?php
final class TempFile
{
    public function __construct(private string $path) {}

    public function remove(): void
    {
        @unlink($this->path);
    }
}
