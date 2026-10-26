<?php
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if (in_array($origin, ['https://app.example.com'], true)) {
    header('Access-Control-Allow-Origin: ' . $origin);
    header('Access-Control-Allow-Credentials: true');
    header('Vary: Origin');
}
