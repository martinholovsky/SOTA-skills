<?php
function fingerprint(string $msg): string
{
    return hash('sha256', $msg);
}
