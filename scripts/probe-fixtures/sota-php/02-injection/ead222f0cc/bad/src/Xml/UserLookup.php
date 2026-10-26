<?php

declare(strict_types=1);

namespace App\Xml;

final class UserLookup
{
    public function find(\DOMXPath $xp, string $name): \DOMNodeList
    {
        return $xp->query("//user[name='$name']");
    }
}
