<?php
function store_email(PDO $db, int $id, string $email): void
{
    $db->prepare('UPDATE users SET email = ? WHERE id = ?')
       ->execute([$email, $id]);
}
