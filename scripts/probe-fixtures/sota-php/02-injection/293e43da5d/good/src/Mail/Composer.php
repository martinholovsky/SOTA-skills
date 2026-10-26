<?php

declare(strict_types=1);

namespace App\Mail;

final class Composer
{
    public function body(\Twig\Environment $twig, array $vars): string
    {
        return $twig->render('mail/welcome.html.twig', $vars);
    }
}
