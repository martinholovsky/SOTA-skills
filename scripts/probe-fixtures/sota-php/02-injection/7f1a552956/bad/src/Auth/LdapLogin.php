<?php
declare(strict_types=1);

function ldap_login($c, string $user, string $pw): bool
{
    if ($pw === '') { return false; }
    $dn = 'uid=' . ldap_escape($user, '', LDAP_ESCAPE_DN) . ',ou=people,dc=example,dc=org';
    return ldap_bind($c, $dn, $pw);
}
