<?php

namespace App\Services;

use Exception;
use ZipArchive;

class TpkjPackageProcessor
{
    protected string $passphrase;
    protected array $anonymizationIndex = [];

    public function __construct(?string $passphrase = null)
    {
        $this->passphrase = $passphrase ?? (function_exists('config') ? config('services.pysync.key', env('PYSYNC_ENCRYPTION_KEY', '')) : '');
    }

    /**
     * Set or override the encryption passphrase.
     */
    public function setPassphrase(string $passphrase): self
    {
        $this->passphrase = $passphrase;
        return $this;
    }

    /**
     * Load optional .pysync_index.json created when PySync anonymization is enabled.
     */
    public function loadAnonymizationIndex(string $indexFilePath): void
    {
        if (file_exists($indexFilePath)) {
            $json = file_get_contents($indexFilePath);
            $this->anonymizationIndex = json_decode($json, true) ?? [];
        }
    }

    /**
     * Decode metadata from directory and package filename.
     * Example input:  "Packages/252425/252425-1-022426.tpkj.2"
     * Example result: [
     *     'customer_id'   => '252425',
     *     'store_id'      => '252425-1',
     *     'package_date'  => '022426',
     *     'clean_filename'=> '252425-1-022426.tpkj',
     * ]
     */
    public function decodePackageMetadata(string $filePath, ?string $folderName = null): array
    {
        $filename = basename($filePath);

        // 1. Resolve anonymized filenames (e.g. PKG_a3f8.tpkj -> 252425-1-022426.tpkj)
        $realFilename = $this->anonymizationIndex[$filename] ?? $filename;
        $realFolder = ($folderName && isset($this->anonymizationIndex[$folderName])) 
            ? $this->anonymizationIndex[$folderName] 
            : $folderName;

        // 2. Clean trailing version numbers (.tpkj.1, .tpkj.2 -> .tpkj)
        $cleanFilename = preg_replace('/(\\.tpkj).*$/i', '.tpkj', $realFilename);

        // 3. Extract parts (Format: CUSTOMER-STORE-DATE.tpkj)
        $nameWithoutExt = str_ireplace('.tpkj', '', $cleanFilename);
        $parts = explode('-', $nameWithoutExt);

        $customerId = $parts[0] ?? ($realFolder ?? 'Unknown');
        $storeId = (count($parts) >= 2) ? "{$parts[0]}-{$parts[1]}" : $customerId;
        $packageDate = $parts[2] ?? null;

        return [
            'original_filename' => $filename,
            'clean_filename'    => $cleanFilename,
            'customer_id'       => trim($customerId),
            'store_id'          => trim($storeId),
            'package_date'      => $packageDate ? trim($packageDate) : null,
            'is_anonymized'     => ($filename !== $realFilename),
        ];
    }

    /**
     * Decrypts PySync encrypted payload [ 16-byte IV ] + [ Ciphertext ]
     */
    public function decryptPackage(string $encryptedFilePath, ?string $key = null): string|false
    {
        $passphrase = $key ?? $this->passphrase;
        if (empty($passphrase)) {
            throw new Exception("Encryption key is required to decrypt .tpkj package.");
        }

        if (!file_exists($encryptedFilePath)) {
            if (class_exists('\Illuminate\Support\Facades\Log')) {
                \Illuminate\Support\Facades\Log::error("Package file does not exist: {$encryptedFilePath}");
            }
            return false;
        }

        $rawPayload = file_get_contents($encryptedFilePath);
        
        // If file is already unencrypted (starts with ZIP signature PK\x03\x04)
        if (str_starts_with($rawPayload, "PK\x03\x04")) {
            return $rawPayload;
        }

        if (strlen($rawPayload) <= 16) {
            if (class_exists('\Illuminate\Support\Facades\Log')) {
                \Illuminate\Support\Facades\Log::error("Invalid .tpkj package payload size.");
            }
            return false;
        }

        // Derive 32-byte AES key using SHA-256 (matches core/crypto.py derive_aes_key)
        $aesKey = hash('sha256', $passphrase, true);

        // Extract 16-byte IV and Ciphertext
        $iv = substr($rawPayload, 0, 16);
        $ciphertext = substr($rawPayload, 16);

        // Decrypt AES-256-CBC
        $decrypted = openssl_decrypt($ciphertext, 'aes-256-cbc', $aesKey, OPENSSL_RAW_DATA, $iv);

        if ($decrypted === false || !str_starts_with($decrypted, "PK\x03\x04")) {
            if (class_exists('\Illuminate\Support\Facades\Log')) {
                \Illuminate\Support\Facades\Log::error("Decryption failed or invalid ZIP header for file: {$encryptedFilePath}");
            }
            return false;
        }

        return $decrypted;
    }

    /**
     * Decrypts and extracts package contents to local destination directory.
     */
    public function processAndExtract(string $tpkjFilePath, string $extractToDirectory, ?string $key = null): array
    {
        $metadata = $this->decodePackageMetadata($tpkjFilePath);
        $decryptedBytes = $this->decryptPackage($tpkjFilePath, $key);

        if ($decryptedBytes === false) {
            throw new Exception("Failed to decrypt package: {$tpkjFilePath}");
        }

        if (!is_dir($extractToDirectory)) {
            mkdir($extractToDirectory, 0755, true);
        }

        $tempZipPath = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'tpkj_temp_' . uniqid() . '.zip';
        file_put_contents($tempZipPath, $decryptedBytes);

        $zip = new ZipArchive();
        if ($zip->open($tempZipPath) === true) {
            $zip->extractTo($extractToDirectory);
            $zip->close();
            @unlink($tempZipPath);
        } else {
            @unlink($tempZipPath);
            throw new Exception("Failed to extract ZIP payload for package: {$tpkjFilePath}");
        }

        return [
            'metadata' => $metadata,
            'extracted_path' => $extractToDirectory,
        ];
    }
}
