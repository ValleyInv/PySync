# Modern QSS Stylesheets for PySync Windows Application

DARK_THEME = """
QMainWindow, QDialog {
    background-color: #18191c;
    color: #dbdee1;
    font-family: 'Segoe UI', sans-serif;
}

QWidget {
    color: #dbdee1;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

/* Header & Toolbars */
#headerBar {
    background-color: #1e1f22;
    border-bottom: 1px solid #2b2d31;
    padding: 8px 12px;
}

#searchEdit {
    background-color: #2b2d31;
    border: 1px solid #383a40;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f2f3f5;
    font-size: 13px;
}

#searchEdit:focus {
    border: 1px solid #5865f2;
    background-color: #313338;
}

/* Sidebar */
#sidebar {
    background-color: #111214;
    border-right: 1px solid #2b2d31;
}

#sidebar QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}

#sidebar QListWidget::item {
    padding: 10px 14px;
    border-radius: 6px;
    margin: 2px 8px;
    color: #949ba4;
    font-weight: 500;
}

#sidebar QListWidget::item:hover {
    background-color: #2b2d31;
    color: #f2f3f5;
}

#sidebar QListWidget::item:selected {
    background-color: #5865f2;
    color: #ffffff;
    font-weight: bold;
}

/* Action Buttons */
QPushButton {
    background-color: #2b2d31;
    color: #f2f3f5;
    border: 1px solid #383a40;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #35373c;
    border-color: #4e5058;
}

QPushButton:pressed {
    background-color: #1e1f22;
}

QPushButton#primaryBtn {
    background-color: #5865f2;
    color: #ffffff;
    border: none;
}

QPushButton#primaryBtn:hover {
    background-color: #4752c4;
}

QPushButton#primaryBtn:pressed {
    background-color: #3c45a5;
}

/* Table View */
QTableWidget {
    background-color: #1e1f22;
    border: none;
    gridline-color: #2b2d31;
    selection-background-color: #2b2d31;
    selection-color: #ffffff;
}

QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #2b2d31;
}

QTableWidget::item:hover {
    background-color: #2b2d31;
}

QTableWidget::item:selected {
    background-color: #35373c;
    color: #5865f2;
    font-weight: bold;
}

QHeaderView::section {
    background-color: #18191c;
    color: #949ba4;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #2b2d31;
    font-weight: bold;
    font-size: 12px;
}

/* Details Panel */
#detailPanel {
    background-color: #1e1f22;
    border-left: 1px solid #2b2d31;
    padding: 16px;
}

#previewArea {
    background-color: #111214;
    border: 1px solid #2b2d31;
    border-radius: 8px;
    padding: 10px;
}

/* Status Bar & Transfer Bar */
#statusBar {
    background-color: #111214;
    border-top: 1px solid #2b2d31;
    color: #949ba4;
    padding: 6px 12px;
    font-size: 12px;
}

/* Context Menu */
QMenu {
    background-color: #2b2d31;
    border: 1px solid #383a40;
    border-radius: 6px;
    padding: 4px;
}

QMenu::item {
    padding: 6px 20px 6px 10px;
    border-radius: 4px;
    color: #dbdee1;
}

QMenu::item:selected {
    background-color: #5865f2;
    color: #ffffff;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #1e1f22;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2b2d31;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #4e5058;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog {
    background-color: #f8f9fa;
    color: #212529;
    font-family: 'Segoe UI', sans-serif;
}

QWidget {
    color: #212529;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

#headerBar {
    background-color: #ffffff;
    border-bottom: 1px solid #e9ecef;
    padding: 8px 12px;
}

#searchEdit {
    background-color: #f1f3f5;
    border: 1px solid #ced4da;
    border-radius: 6px;
    padding: 6px 12px;
    color: #212529;
}

#searchEdit:focus {
    border: 1px solid #0d6efd;
    background-color: #ffffff;
}

#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e9ecef;
}

#sidebar QListWidget {
    background-color: transparent;
    border: none;
}

#sidebar QListWidget::item {
    padding: 10px 14px;
    border-radius: 6px;
    margin: 2px 8px;
    color: #495057;
    font-weight: 500;
}

#sidebar QListWidget::item:hover {
    background-color: #e9ecef;
    color: #212529;
}

#sidebar QListWidget::item:selected {
    background-color: #0d6efd;
    color: #ffffff;
    font-weight: bold;
}

QPushButton {
    background-color: #f1f3f5;
    color: #212529;
    border: 1px solid #ced4da;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #e2e6ea;
}

QPushButton#primaryBtn {
    background-color: #0d6efd;
    color: #ffffff;
    border: none;
}

QPushButton#primaryBtn:hover {
    background-color: #0b5ed7;
}

QTableWidget {
    background-color: #ffffff;
    border: none;
    gridline-color: #f1f3f5;
}

QTableWidget::item {
    padding: 8px 10px;
    border-bottom: 1px solid #f1f3f5;
}

QTableWidget::item:hover {
    background-color: #f8f9fa;
}

QTableWidget::item:selected {
    background-color: #e7f1ff;
    color: #0d6efd;
    font-weight: bold;
}

QHeaderView::section {
    background-color: #f8f9fa;
    color: #6c757d;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #dee2e6;
    font-weight: bold;
}

#detailPanel {
    background-color: #ffffff;
    border-left: 1px solid #e9ecef;
    padding: 16px;
}

#previewArea {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 10px;
}

#statusBar {
    background-color: #ffffff;
    border-top: 1px solid #e9ecef;
    color: #6c757d;
    padding: 6px 12px;
}
"""
