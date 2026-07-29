<?php

/**
 * Standalone CLI test script for decoding and decrypting PySync .tpkj files.
 *
 * Usage:
 *   php example_standalone.php <path_to_tpkj_file> <encryption_passphrase> [output_directory]
 */

require_once __DIR__ . '/app/Services/TpkjPackageProcessor.php';

use App\Services\TpkjPackageProcessor;

if ($argc < 3) {
    echo "Usage: php example_standalone.php <path_to_tpkj_file> <passphrase> [output_dir]\n";
    echo "Example: php example_standalone.php ./252425-1-022426.tpkj.2 SecretKey123 ./extracted_output\n";
    exit(1);
}

$filePath   = $argv[1];
$passphrase = $argv[2];
$outputDir  = $argv[3] ?? __DIR__ . '/extracted';

$processor = new TpkjPackageProcessor($passphrase);

echo "=========================================\n";
echo "PySync .tpkj Package Processor (PHP)\n";
echo "=========================================\n";

// 1. Decode metadata
$metadata = $processor->decodePackageMetadata($filePath);
echo "Original Filename: " . $metadata['original_filename'] . "\n";
echo "Clean Filename:    " . $metadata['clean_filename'] . "\n";
echo "Customer ID:       " . $metadata['customer_id'] . "\n";
echo "Store ID:          " . $metadata['store_id'] . "\n";
echo "Package Date:      " . ($metadata['package_date'] ?? 'N/A') . "\n";
echo "-----------------------------------------\n";

// 2. Process and Extract
try {
    echo "Decrypting and extracting contents...\n";
    $result = $processor->processAndExtract($filePath, $outputDir, $passphrase);
    echo "SUCCESS! Files extracted to: " . realpath($result['extracted_path']) . "\n";
} catch (Exception $e) {
    echo "ERROR: " . $e->getMessage() . "\n";
    exit(1);
}
