<?php
function store_password(PDO $db, int $id, string $pw): void
{
    $db->prepare('UPDATE users SET hash = ? WHERE id = ?')
       ->execute([password_hash($pw, PASSWORD_DEFAULT), $id]);
}
