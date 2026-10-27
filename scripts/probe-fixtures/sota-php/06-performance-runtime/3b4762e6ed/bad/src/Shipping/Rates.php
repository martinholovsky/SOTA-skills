<?php
function rates(array $skus): array
{
    $out = [];
    foreach ($skus as $sku) {
        $ch = curl_init('https://rates.example.com/v1/' . rawurlencode($sku));
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);
        $out[$sku] = curl_exec($ch);
        curl_close($ch);
    }
    return $out;
}
