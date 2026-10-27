<?php
function unpack_upload(string $gzPath, string $dest): void
{
    $data = gzdecode((string) file_get_contents($gzPath));
    file_put_contents($dest . '/import.csv', $data);
}
