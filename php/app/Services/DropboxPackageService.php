<?php

namespace App\Services;

use Exception;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class DropboxPackageService
{
    protected string $accessToken;
    protected string $refreshToken;
    protected string $appKey;
    protected string $appSecret;
    protected string $basePath;

    public function __construct()
    {
        $this->accessToken = env('DROPBOX_ACCESS_TOKEN', '');
        $this->refreshToken = env('DROPBOX_REFRESH_TOKEN', '');
        $this->appKey = env('DROPBOX_APP_KEY', '');
        $this->appSecret = env('DROPBOX_APP_SECRET', '');
        $this->basePath = env('DROPBOX_PACKAGES_PATH', '/Nor Cal office misc/Packages');
    }

    /**
     * Get a valid access token, auto-refreshing via OAuth2 if refresh_token is configured.
     */
    public function getValidAccessToken(): string
    {
        if (!empty($this->accessToken)) {
            return $this->accessToken;
        }

        if (empty($this->refreshToken) || empty($this->appKey) || empty($this->appSecret)) {
            throw new Exception("Dropbox credentials missing. Set DROPBOX_REFRESH_TOKEN, DROPBOX_APP_KEY, and DROPBOX_APP_SECRET in .env");
        }

        $response = Http::asForm()->post('https://api.dropbox.com/oauth2/token', [
            'grant_type'    => 'refresh_token',
            'refresh_token' => $this->refreshToken,
            'client_id'     => $this->appKey,
            'client_secret' => $this->appSecret,
        ]);

        if ($response->failed()) {
            throw new Exception("Failed to refresh Dropbox access token: " . $response->body());
        }

        $data = $response->json();
        $this->accessToken = $data['access_token'] ?? '';

        return $this->accessToken;
    }

    /**
     * List all .tpkj package files on Dropbox Cloud.
     */
    public function listRemotePackages(string $subFolder = ""): array
    {
        $token = $this->getValidAccessToken();
        $targetPath = rtrim($this->basePath . '/' . ltrim($subFolder, '/'), '/');

        $response = Http::withToken($token)
            ->post('https://api.dropboxapi.com/2/files/list_folder', [
                'path' => $targetPath,
                'recursive' => true,
            ]);

        if ($response->failed()) {
            throw new Exception("Dropbox API list_folder failed: " . $response->body());
        }

        $entries = $response->json()['entries'] ?? [];
        $packages = [];

        foreach ($entries as $entry) {
            if ($entry['.tag'] === 'file' && preg_match('/\.tpkj(\.\d+)?$/i', $entry['name'])) {
                $packages[] = [
                    'name'         => $entry['name'],
                    'path_lower'   => $entry['path_lower'],
                    'path_display' => $entry['path_display'],
                    'size'         => $entry['size'] ?? 0,
                    'server_modified' => $entry['server_modified'] ?? '',
                ];
            }
        }

        return $packages;
    }

    /**
     * Download a .tpkj package directly from Dropbox Cloud to local storage path.
     */
    public function downloadPackage(string $remotePath, string $localSavePath): string
    {
        $token = $this->getValidAccessToken();

        File::ensureDirectoryExists(dirname($localSavePath));

        $response = Http::withToken($token)
            ->withHeaders([
                'Dropbox-API-Arg' => json_encode(['path' => $remotePath])
            ])
            ->post('https://content.dropboxapi.com/2/files/download');

        if ($response->failed()) {
            throw new Exception("Dropbox API download failed for '{$remotePath}': " . $response->body());
        }

        File::put($localSavePath, $response->body());

        return $localSavePath;
    }
}
