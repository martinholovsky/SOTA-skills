<?php
function unpack_upload(string $zipPath, string $dest): void
{
    $zip = new \ZipArchive();
    $zip->open($zipPath);
    $zip->extractTo($dest);
    $zip->close();
}
