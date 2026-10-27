<?php
function each_audit(PDO $db): \Generator
{
    $st = $db->query('SELECT * FROM audit_log');
    while (($row = $st->fetch()) !== false) {
        yield $row;
    }
}
