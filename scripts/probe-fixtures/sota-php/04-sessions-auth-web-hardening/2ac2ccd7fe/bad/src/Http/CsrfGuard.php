<?php
function csrf_ok(string $sent): bool
{
    return hash_equals($_SESSION['csrf'] ?? '', $sent);
}
