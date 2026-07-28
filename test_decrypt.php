<?php

$passphrase = 'NorCalOfficeSecretKey2026';
$key = hash('sha256', $passphrase, true);
$raw = file_get_contents('test_encrypted.enc');
$iv = substr($raw, 0, 16);
$ciphertext = substr($raw, 16);

$decrypted = openssl_decrypt($ciphertext, 'aes-256-cbc', $key, OPENSSL_RAW_DATA, $iv);

echo "Decrypted in PHP: " . $decrypted . "\n";
