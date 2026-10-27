<?php
function csrf_issue(): string
{
    return $_SESSION['csrf'] ??= bin2hex(random_bytes(32));
}
