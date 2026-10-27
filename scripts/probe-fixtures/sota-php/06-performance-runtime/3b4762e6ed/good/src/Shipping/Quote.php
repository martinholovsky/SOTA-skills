<?php
function quote(string $sku): string
{
    $ch = curl_init('https://rates.example.com/v1/' . rawurlencode($sku));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 5);
    $body = curl_exec($ch);
    curl_close($ch);
    return is_string($body) ? $body : '';
}
