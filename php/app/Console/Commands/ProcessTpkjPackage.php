<?php

namespace App\Console\Commands;

use App\Services\DropboxPackageService;
use App\Services\TpkjPackageProcessor;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\File;

class ProcessTpkjPackage extends Command
{
    protected $signature = 'tpkj:process 
        {file? : Path to .tpkj package file or filename in Dropbox/storage}
        {--from-dropbox : Fetch/download package directly from Dropbox Cloud API before processing}
        {--list-dropbox : List available .tpkj packages on Dropbox Cloud API and exit}
        {--keep-local : Do not delete the temporary downloaded package file after processing}
        {--key= : Optional passphrase override if different from PYSYNC_ENCRYPTION_KEY in .env}';

    protected $description = 'Fetches package from Dropbox Cloud, processes/extracts package, and cleans up local temp files to save disk space';

    public function handle(TpkjPackageProcessor $processor, DropboxPackageService $dropbox): int
    {
        // 1. List Dropbox packages if requested
        if ($this->option('list-dropbox')) {
            $this->info("Fetching package list from Dropbox Cloud...");
            try {
                $packages = $dropbox->listRemotePackages();
                if (empty($packages)) {
                    $this->warn("No .tpkj packages found on Dropbox Cloud.");
                    return Command::SUCCESS;
                }

                $rows = array_map(fn($p) => [
                    $p['name'],
                    $p['path_display'],
                    number_format($p['size'] / 1024, 1) . ' KB',
                    $p['server_modified']
                ], $packages);

                $this->table(['Package Name', 'Dropbox Remote Path', 'Size', 'Modified'], $rows);
                return Command::SUCCESS;
            } catch (\Exception $e) {
                $this->error("Dropbox API Error: " . $e->getMessage());
                return Command::FAILURE;
            }
        }

        $givenFile = $this->argument('file');
        if (!$givenFile) {
            $this->error("Please specify a package filename or run 'php artisan tpkj:process --list-dropbox'");
            return Command::FAILURE;
        }

        $customKey = $this->option('key') ?: env('PYSYNC_ENCRYPTION_KEY', config('services.pysync.key', ''));
        if ($customKey) {
            $processor->setPassphrase($customKey);
        }

        $filePath = $givenFile;
        $downloadedTempPath = null;

        try {
            // 2. Fetch directly from Dropbox API if --from-dropbox flag is provided
            if ($this->option('from-dropbox')) {
                $this->info("☁ Fetching '{$givenFile}' from Dropbox Cloud API...");
                $remotePackages = $dropbox->listRemotePackages();
                $match = null;
                foreach ($remotePackages as $pkg) {
                    if (str_ends_with($pkg['name'], $givenFile) || $pkg['name'] === $givenFile) {
                        $match = $pkg;
                        break;
                    }
                }

                if (!$match) {
                    $this->error("Package '{$givenFile}' not found on Dropbox Cloud.");
                    return Command::FAILURE;
                }

                $downloadedTempPath = storage_path("app/private/uploads/temp_" . uniqid() . "_" . $match['name']);
                $this->info("📥 Downloading from Dropbox: {$match['path_display']}");
                $dropbox->downloadPackage($match['path_display'], $downloadedTempPath);
                $filePath = $downloadedTempPath;
                $this->info("✓ Download complete (" . number_format(filesize($filePath) / 1024, 1) . " KB)");
            }

            $this->info("⚙ Processing package: {$filePath}");

            // 3. Decode directory and package metadata
            $metadata = $processor->decodePackageMetadata($filePath);
            $this->table(['Field', 'Value'], [
                ['Clean Filename', $metadata['clean_filename']],
                ['Customer ID',    $metadata['customer_id']],
                ['Store ID',       $metadata['store_id']],
                ['Package Date',   $metadata['package_date'] ?? 'N/A'],
                ['Is Anonymized',  $metadata['is_anonymized'] ? 'Yes' : 'No'],
            ]);

            // 4. Decrypt & Extract
            $outputDir = storage_path("app/extracted/{$metadata['store_id']}");
            $result = $processor->processAndExtract($filePath, $outputDir);
            $this->info("✓ Package successfully decrypted and extracted to: {$result['extracted_path']}");

            return Command::SUCCESS;
        } catch (\Exception $e) {
            $this->error("❌ Error processing package: " . $e->getMessage());
            return Command::FAILURE;
        } finally {
            // 5. Disk-Saver Cleanup: Delete downloaded temporary .tpkj file unless --keep-local is passed
            if ($downloadedTempPath && File::exists($downloadedTempPath)) {
                if (!$this->option('keep-local')) {
                    File::delete($downloadedTempPath);
                    $this->info("🧹 Disk-Saver: Removed temporary downloaded package from local disk.");
                } else {
                    $this->comment("📌 Kept downloaded package at: {$downloadedTempPath}");
                }
            }
        }
    }
}
