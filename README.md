# PySync — Dropbox Packages & Titan Inventory Integration

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://pypi.org/project/PyQt6/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

**PySync** is a modern Windows desktop GUI application built with Python 3.13 and PyQt6. It integrates directly with Dropbox to access, browse, manage, preview, encrypt, and sync inventory package files in **`Dropbox / Nor Cal office misc / Packages`**.

It includes an automated **Titan Customer Package Finder** that scans local inventory directories (e.g. `C:\ProgramData\AST\Titan_Inventory_Control\_Customers` or `Desktop\Incoming`), isolates the highest-version `.tpkj` package files per directory, strips trailing version suffixes (`.1`, `.2`, etc.), encrypts package contents with AES-256-CBC, and batch-transfers clean `.tpkj` files into organized Customer subfolders in Dropbox.

---

## Key Features

### 1. Dual-Mode Dropbox Integration & Disk Saver
- **Local Sync Mode**: Automatic auto-detection of your local Dropbox folder (`C:\Users\<User>\Dropbox\Nor Cal office misc\Packages`) for instant filesystem operations.
- **Disk-Saver Pure Cloud API Mode**: Connects directly to Dropbox Cloud API via access tokens to stream file lists, metadata, and previews **without consuming local hard drive space**.
- **Smart LRU Temp Cache**: On-demand file downloads are saved to `%TEMP%\PySync_Cache` and automatically purged when total cache size exceeds your configured limit (e.g. 500 MB).

### 2. Titan Customer Package Scanner (`*.tpkj.*`)
- **Automated Background Scanner**: Scans `C:\ProgramData\AST\Titan_Inventory_Control\_Customers` across 17,000+ customer directories in a background thread (`QThread`) without UI freezes.
- **Editable Scan Target & Presets**: Easily switch target directories (e.g. `Desktop\Incoming` or custom network folders) with 1-click presets and folder browser.
- **Highest Version Isolation**: Evaluates version suffixes (`.tpkj.1`, `.tpkj.2`, `.tpkj.15`) and keeps only the single highest-numbered package file per directory.
- **Clean Filename Sanitization**: Automatically strips trailing `.#` version numbers (e.g., `252425-1-022426.tpkj.2` $\rightarrow$ `252425-1-022426.tpkj`) when transferring files to Dropbox.
- **Fast Debounced Search**: Fast 60fps search filtering across Customer Name, Store Name, or File Name with 300ms debounced queries and rendering limits.

### 3. Customer Subfolder Organization
- **Clean Dropbox Hierarchy**: Automatically organizes transferred packages into Customer subfolders (`Dropbox / Packages / <Customer_Name> / <Package_Name>.tpkj`), preventing flat 17,000-file slowdowns in Windows File Explorer and Dropbox sync.
- Toggleable via **⚙ Settings** (`"preserve_customer_folders": true`).

### 4. Package Security & AES-256-CBC Encryption
- **AES-256-CBC Encryption**: Optionally encrypts package contents before sending to Dropbox using AES-256-CBC with a 16-byte random IV and SHA-256 derived secret key.
- **Zero-Dependency Laravel PHP Decryption**: Includes native PHP decryption using built-in `openssl_decrypt()` for seamless processing in Laravel backend systems.

### 5. Modern Windows 11 Desktop GUI
- **Dual View Modes**: Switch between **📋 Table View** and **🔲 Grid View**.
- **Live Preview Panel**: Integrated side panel displaying image thumbnails (PNG, JPG, WEBP, SVG) and document text previews (TXT, CSV, JSON, LOG).
- **Drag & Drop Uploads**: Drag external files or packages directly into PySync to upload/copy into Dropbox.
- **Theme Engine**: Toggle between sleek **Dark Mode** and **Light Mode** styling.

---

## Laravel PHP Decryption Guide

PySync encrypts package payloads in the format `[ 16-byte IV ] + [ AES-256-CBC Ciphertext ]`. You can decrypt these files in Laravel PHP with zero external composer dependencies:

```php
namespace App\Services;

class PackageDecryptor
{
    /**
     * Decrypts a PySync encrypted .tpkj package file.
     *
     * @param string $encryptedFilePath Full path to encrypted package file
     * @param string $secretPassphrase The secret key configured in PySync settings
     * @return string|false Decrypted binary contents or false on failure
     */
    public static function decryptFile(string $encryptedFilePath, string $secretPassphrase): string|false
    {
        if (!file_exists($encryptedFilePath)) {
            return false;
        }

        // Derive 32-byte raw binary AES key via SHA-256
        $key = hash('sha256', $secretPassphrase, true);

        // Read payload
        $rawPayload = file_get_contents($encryptedFilePath);
        if (strlen($rawPayload) <= 16) {
            return false;
        }

        // Extract 16-byte IV and Ciphertext
        $iv = substr($rawPayload, 0, 16);
        $ciphertext = substr($rawPayload, 16);

        // Decrypt using OpenSSL
        return openssl_decrypt($ciphertext, 'aes-256-cbc', $key, OPENSSL_RAW_DATA, $iv);
    }
}
```

---

## Getting Started

### Prerequisites
- Windows 10 / 11
- Python 3.10+ (Tested on Python 3.13)

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/ValleyInv/PySync.git
   cd PySync
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Launching PySync
Run the application:
```bash
python main.py
```

---

## Configuration & Dropbox Token Setup

1. Launch PySync and click **⚙ Settings** in the top right.
2. Under **Dropbox Cloud API Connection**, click **🔑 How to get a Token?** or follow these steps:
   - Go to the [Dropbox App Console](https://www.dropbox.com/developers/apps).
   - Create an app with **Scoped Access** and **Full Dropbox** access.
   - Under **Permissions**, enable: `files.metadata.read`, `files.content.read`, `files.content.write`.
   - Under **Settings**, click **Generate** under *Generated Access Token*.
3. Paste your token into PySync, click **🔌 Test Token**, check **⚡ Enable Pure Cloud Mode**, and click **💾 Save Settings**.

---

## Project Structure

```
PySync/
├── main.py                     # Application entry point
├── config.py                   # Path auto-detection, JSON settings persistence
├── requirements.txt            # Python dependencies (PyQt6, cryptography, dropbox, pillow, requests)
├── README.md                   # Comprehensive documentation & PHP guide
├── core/
│   ├── models.py               # PackageItem & ScannedPackageItem data models
│   ├── crypto.py               # AES-256-CBC encryption & key derivation module
│   ├── local_provider.py       # Windows filesystem manager & Explorer integration
│   ├── cloud_provider.py       # Dropbox API Cloud client with memory thumbnail streaming
│   ├── hybrid_engine.py        # Local + Cloud coordinator and LRU temp cache manager
│   └── scanner.py              # Background worker thread scanning *.tpkj.* files
└── ui/
    ├── styles.py               # Dark & Light QSS stylesheets
    ├── main_window.py          # Central Window layout & event dispatcher
    └── components/
        ├── header_bar.py       # Path breadcrumbs, search input, toolbar actions
        ├── sidebar.py          # Category filters and live sync status indicators
        ├── file_view.py        # Table & Grid views with context menus & drag-and-drop
        ├── detail_panel.py     # Live document & image previewer
        ├── transfer_bar.py     # Status updates and progress queue
        ├── settings_dialog.py  # Path selector, token test, crypto, and disk saver settings
        └── scanner_dialog.py   # Package Finder dialog with debounced search & path presets
```

---

## License
Internal Tool — Nor Cal Office Inventory Management.
