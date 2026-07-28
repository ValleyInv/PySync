# PySync — Dropbox Packages & Titan Inventory Integration

**PySync** is a modern Windows desktop GUI application built with Python 3.13 and PyQt6. It integrates directly with Dropbox to access, manage, preview, and sync inventory package files in **`Dropbox / Nor Cal office misc / Packages`**.

It includes an automated **Titan Customer Package Finder** that scans local inventory directories (e.g. `C:\ProgramData\AST\Titan_Inventory_Control\_Customers` or `Desktop\Incoming`), isolates the highest-version `.tpkj` package files per directory, strips trailing version suffixes (`.1`, `.2`, etc.), and batch-transfers clean `.tpkj` files into your Dropbox target directory.

---

## Key Features

### 1. Dual-Mode Dropbox Integration
- **Local Sync Mode**: Automatic auto-detection of your local Dropbox folder (`C:\Users\<User>\Dropbox\Nor Cal office misc\Packages`) for instant filesystem operations.
- **Disk-Saver Pure Cloud API Mode**: Uses official Dropbox Cloud API tokens to stream file lists, metadata, and previews directly from the cloud **without consuming local hard drive space**.

### 2. Titan Customer Package Scanner (`*.tpkj.*`)
- **Automated Directory Scanner**: Scans `C:\ProgramData\AST\Titan_Inventory_Control\_Customers` across 17,000+ customer directories in a background thread without freezing the interface.
- **Editable & Custom Scan Targets**: Easily switch scanning target paths (e.g. `Desktop\Incoming` or custom network folders) with 1-click presets and directory browser.
- **Highest Version Isolation**: Evaluates version suffixes (`.tpkj.1`, `.tpkj.2`, `.tpkj.15`) and keeps only the highest-numbered package file per directory.
- **Clean Filename Sanitization**: Automatically strips trailing `.#` version numbers (e.g., `252425-1-022426.tpkj.2` $\rightarrow$ `252425-1-022426.tpkj`) when transferring files to Dropbox.
- **Instant Debounced Search**: Fast 60fps search filtering across Customer Name, Store Name, or File Name with instant 300ms debounced queries.

### 3. On-Demand Streaming & Auto Temp Cache
- **On-Demand File Downloads**: Cloud files are downloaded only when explicitly opened.
- **Auto LRU Cache Purging**: Temporary files in `%TEMP%\PySync_Cache` are monitored and automatically purged when total cache size exceeds your configured limit (e.g. 500 MB).

### 4. Modern Windows 11 Desktop GUI
- **Dual View Modes**: Switch between **📋 Table View** and **🔲 Grid View**.
- **Live Preview Panel**: Integrated side panel displaying image thumbnails (PNG, JPG, WEBP, SVG) and document text previews (TXT, CSV, JSON, LOG).
- **Drag & Drop Uploads**: Drag external files or packages directly into PySync to upload/copy into Dropbox.
- **Theme Engine**: Toggle between sleek **Dark Mode** and **Light Mode** styling.

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
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Launching PySync
Run the application using Python:
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
├── main.py                     # Entry point & QApplication runner
├── config.py                   # Path auto-detection, JSON settings persistence
├── requirements.txt            # Python dependencies (PyQt6, dropbox, pillow, requests)
├── core/
│   ├── models.py               # PackageItem and ScannedPackageItem data structures
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
        ├── settings_dialog.py  # Path selector, token test, and disk saver settings
        └── scanner_dialog.py   # Titan Customer Package Finder dialog with debounced search
```

---

## License
Internal Tool — Nor Cal Office Inventory Management.
