<?php
declare(strict_types=1);

function db_login(PDO $db, string $user, string $pw): bool
{
    $st = $db->prepare('SELECT hash FROM users WHERE name = ?');
    $st->execute([$user]);
    return password_verify($pw, (string) $st->fetchColumn());
}
