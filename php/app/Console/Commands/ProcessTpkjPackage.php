<?php

namespace App\Console\Commands;

use App\Services\TpkjPackageProcessor;
use Illuminate\Console\Command;

class ProcessTpkjPackage extends Command
{
    protected $signature = 'tpkj:process {file : Path to .tpkj package} {--key= : Secret passphrase configured in PySync}';
    protected $description = 'Decodes directory/package metadata and decrypts .tpkj package for local processing';

    public function handle(TpkjPackageProcessor $processor): int
    {
        $filePath = $this->argument('file');
        $customKey = $this->option('key');

        if ($customKey) {
            $processor->setPassphrase($customKey);
        }

        $this->info("Processing Titan package file: {$filePath}");

        // 1. Decode directory and package metadata
        $metadata = $processor->decodePackageMetadata($filePath);
        $this->table(['Field', 'Value'], [
            ['Clean Filename', $metadata['clean_filename']],
            ['Customer ID',    $metadata['customer_id']],
            ['Store ID',       $metadata['store_id']],
            ['Package Date',   $metadata['package_date'] ?? 'N/A'],
            ['Is Anonymized',  $metadata['is_anonymized'] ? 'Yes' : 'No'],
        ]);

        // 2. Decrypt & Extract
        $outputDir = storage_path("app/extracted/{$metadata['store_id']}");
        
        try {
            $result = $processor->processAndExtract($filePath, $outputDir, $customKey);
            $this->info("Package successfully decrypted and extracted to: {$result['extracted_path']}");
            return Command::SUCCESS;
        } catch (\Exception $e) {
            $this->error("Error: " . $e->getMessage());
            return Command::FAILURE;
        }
    }
}
