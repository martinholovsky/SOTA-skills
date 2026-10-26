<?php

declare(strict_types=1);

namespace App\Mail;

final class Composer
{
    public function body(\Twig\Environment $twig, string $tpl, array $vars): string
    {
        return $twig->createTemplate($tpl)->render($vars);
    }
}
