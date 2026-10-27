<?php
function all_audit(PDO $db): array
{
    return $db->query('SELECT * FROM audit_log')->fetchAll();
}
