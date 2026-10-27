<?php
function rates(array $skus): array
{
    $mh = curl_multi_init();
    $handles = [];
    foreach ($skus as $sku) {
        $ch = curl_init('https://rates.example.com/v1/' . rawurlencode($sku));
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);
        curl_multi_add_handle($mh, $ch);
        $handles[$sku] = $ch;
    }
    do {
        curl_multi_exec($mh, $running);
        curl_multi_select($mh);
    } while ($running > 0);
    $out = [];
    foreach ($handles as $sku => $ch) {
        $out[$sku] = curl_multi_getcontent($ch);
        curl_multi_remove_handle($mh, $ch);
    }
    return $out;
}
