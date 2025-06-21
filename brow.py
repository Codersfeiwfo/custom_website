from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QPushButton, QLineEdit, QWidget,
    QTabWidget, QAction, QFileDialog, QToolBar, QComboBox, QListWidget,
    QShortcut, QDialog
)
from PyQt5.QtWebEngineWidgets import (
    QWebEngineView, QWebEngineDownloadItem, QWebEngineProfile, QWebEnginePage
)
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtGui import QKeySequence
import sys
import json
import os
import speech_recognition as sr

ONE_UI_PRIMARY = "#1A73E8"
ONE_UI_BACKGROUND = "#BEC8D8"
ONE_UI_BUTTON_BG = "#A3AFC2"
ONE_UI_BUTTON_HOVER = "#AFBBCE"
ONE_UI_TEXT = "#222222"


class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(parent)
        self.setProfile(profile)


class WebBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Custom Web Browser - One UI 7 Style')
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(f"background-color: {ONE_UI_BACKGROUND}; color: {ONE_UI_TEXT};")

        self.homepage = self.load_custom_homepage()
        self.bookmarks = []
        self.incognito_mode = False
        self.history_file = "history.json"
        self.history = self.load_history()
        self.downloads = []

        self.search_engines = {
            'Google': 'https://www.google.com/search?q={}',
            'Bing': 'https://www.bing.com/search?q={}',
            'DuckDuckGo': 'https://duckduckgo.com/?q={}'
        }
        self.selected_search_engine = 'Google'

        self._create_menu()
        self._create_toolbar()
        self._create_tabs()
        self._create_shortcuts()
        self.new_tab()

    def _create_menu(self):
        menubar = self.menuBar()
        menubar.setStyleSheet(f"background-color: {ONE_UI_BACKGROUND}; color: {ONE_UI_TEXT};")

        file_menu = menubar.addMenu('File')

        bookmark_action = QAction('Save Bookmark', self)
        bookmark_action.triggered.connect(self.save_bookmark)
        file_menu.addAction(bookmark_action)

        set_homepage_action = QAction('Set Custom Homepage', self)
        set_homepage_action.triggered.connect(self.set_custom_homepage)
        file_menu.addAction(set_homepage_action)

        download_manager_action = QAction('Download Manager', self)
        download_manager_action.triggered.connect(self.show_download_manager)
        file_menu.addAction(download_manager_action)

    def _create_toolbar(self):
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.toolbar.setStyleSheet(f"""
            QToolBar {{
                background-color: {ONE_UI_BACKGROUND};
                border-bottom: 1px solid #c0c0c0;
                padding: 8px 12px;
            }}
        """)
        self.addToolBar(self.toolbar)

        def style_button(btn):
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {ONE_UI_BUTTON_BG};
                    border: none;
                    border-radius: 10px;
                    padding: 6px 14px;
                    font-weight: 600;
                    color: {ONE_UI_TEXT};
                }}
                QPushButton:hover {{
                    background-color: {ONE_UI_BUTTON_HOVER};
                }}
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(36)

        self.back_button = QPushButton('◀')
        self.forward_button = QPushButton('▶')
        self.reload_button = QPushButton('⟳')
        self.incognito_button = QPushButton('Incognito OFF')

        for btn in [self.back_button, self.forward_button, self.reload_button, self.incognito_button]:
            style_button(btn)

        self.history_dropdown = QComboBox()
        self.history_dropdown.addItem('History')
        self.update_history_dropdown()
        self.history_dropdown.setStyleSheet(f"""
            QComboBox {{
                background-color: {ONE_UI_BUTTON_BG};
                border-radius: 10px;
                padding: 6px 12px;
                font-weight: 600;
                color: {ONE_UI_TEXT};
                min-width: 120px;
            }}
            QComboBox:hover {{
                background-color: {ONE_UI_BUTTON_HOVER};
            }}
        """)

        self.search_dropdown = QComboBox()
        self.search_dropdown.addItems(list(self.search_engines.keys()))
        self.search_dropdown.setStyleSheet(self.history_dropdown.styleSheet())

        self.new_tab_button = QPushButton('+')
        self.voice_search_button = QPushButton('🎤')

        for btn in [self.new_tab_button, self.voice_search_button]:
            style_button(btn)
            btn.setFixedWidth(40)

        self.back_button.clicked.connect(self.go_back)
        self.forward_button.clicked.connect(self.go_forward)
        self.reload_button.clicked.connect(self.reload_page)
        self.incognito_button.clicked.connect(self.toggle_incognito_mode)
        self.history_dropdown.activated[str].connect(self.load_from_history)
        self.new_tab_button.clicked.connect(self.new_tab)
        self.search_dropdown.activated[str].connect(self.update_search_engine)
        self.voice_search_button.clicked.connect(self.voice_search)

        self.toolbar.addWidget(self.back_button)
        self.toolbar.addWidget(self.forward_button)
        self.toolbar.addWidget(self.reload_button)
        self.toolbar.addWidget(self.incognito_button)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.search_dropdown)
        self.toolbar.addWidget(self.history_dropdown)
        self.toolbar.addSeparator()
        self.toolbar.addWidget(self.new_tab_button)
        self.toolbar.addWidget(self.voice_search_button)

    def _create_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tabs)

    def _create_shortcuts(self):
        self.add_shortcut(QKeySequence("Ctrl+T"), self.new_tab)
        self.add_shortcut(QKeySequence("Ctrl+W"), self.close_current_tab)
        self.add_shortcut(QKeySequence("Ctrl+L"), self.voice_search)
        for i in range(1, 10):
            self.add_shortcut(QKeySequence(f"Ctrl+{i}"), lambda _, idx=i-1: self.switch_tab(idx))

    def add_shortcut(self, key_sequence, callback):
        shortcut = QShortcut(key_sequence, self)
        shortcut.activated.connect(callback)

    def new_tab(self, url=None):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        url_bar = QLineEdit()
        url_bar.setPlaceholderText('Enter URL and press Enter...')
        url_bar.setStyleSheet(f"""
            QLineEdit {{
                border: 2px solid {ONE_UI_BUTTON_BG};
                border-radius: 12px;
                padding: 8px 12px;
                font-size: 14px;
                background-color: white;
                color: {ONE_UI_TEXT};
            }}
            QLineEdit:focus {{
                border-color: {ONE_UI_PRIMARY};
                background-color: #fff;
            }}
        """)
        layout.addWidget(url_bar)

        browser = QWebEngineView()
        if self.incognito_mode:
            profile = QWebEngineProfile()
            page = CustomWebEnginePage(profile)
            browser.setPage(page)
        else:
            browser.setPage(QWebEnginePage(QWebEngineProfile.defaultProfile()))

        browser.page().profile().downloadRequested.connect(self.handle_download)
        layout.addWidget(browser)

        url_bar.returnPressed.connect(lambda: self.load_url(browser, url_bar))

        if not url:
            url = self.homepage
        browser.setUrl(QUrl(url))

        self.tabs.addTab(tab, "New Tab")
        self.tabs.setCurrentWidget(tab)

    def load_url(self, browser, url_bar):
        url = url_bar.text()
        if not url.startswith('http'):
            search_url = self.search_engines[self.selected_search_engine].format(url)
            browser.setUrl(QUrl(search_url))
        else:
            browser.setUrl(QUrl(url))
        if not self.incognito_mode:
            self.history.append(url)
            self.save_history()
            self.update_history_dropdown()

    def voice_search(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            try:
                audio = recognizer.listen(source, timeout=5)
                query = recognizer.recognize_google(audio).strip()
                print(f"Recognized: {query}")

                if query.startswith("http") or "." in query:
                    url = query if query.startswith("http") else "http://" + query
                    self.new_tab(url)
                else:
                    search_url = self.search_engines[self.selected_search_engine].format(query)
                    self.new_tab(search_url)

            except sr.UnknownValueError:
                print("Could not understand audio")
            except sr.RequestError:
                print("Speech recognition service is unavailable")

    def set_custom_homepage(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.AnyFile)
        file_dialog.setNameFilter("HTML Files (*.html);;All Files (*)")

        if file_dialog.exec_():
            homepage_path = file_dialog.selectedFiles()[0]
            with open("custom_homepage.txt", "w") as file:
                file.write(homepage_path)
            self.homepage = homepage_path
            print(f'Custom homepage set: {homepage_path}')

    def save_bookmark(self):
        current_browser = self.tabs.currentWidget().layout().itemAt(1).widget()
        url = current_browser.url().toString()
        self.bookmarks.append(url)
        with open("bookmarks.json", "w") as file:
            json.dump(self.bookmarks, file)
        print(f'Bookmark saved: {url}')

    def go_back(self):
        self.tabs.currentWidget().layout().itemAt(1).widget().back()

    def go_forward(self):
        self.tabs.currentWidget().layout().itemAt(1).widget().forward()

    def reload_page(self):
        self.tabs.currentWidget().layout().itemAt(1).widget().reload()

    def toggle_incognito_mode(self):
        self.incognito_mode = not self.incognito_mode
        self.incognito_button.setText('Incognito ON' if self.incognito_mode else 'Incognito OFF')
        print("Incognito Mode:", "Enabled" if self.incognito_mode else "Disabled")

    def update_search_engine(self, engine):
        self.selected_search_engine = engine
        print(f'Search engine updated to: {self.selected_search_engine}')

    def save_history(self):
        if not self.incognito_mode:
            with open(self.history_file, "w") as file:
                json.dump(self.history, file)

    def load_history(self):
        return json.load(open(self.history_file)) if os.path.exists(self.history_file) else []

    def update_history_dropdown(self):
        self.history_dropdown.clear()
        self.history_dropdown.addItem('History')
        for url in reversed(self.history):
            self.history_dropdown.addItem(url)

    def load_from_history(self, url):
        if url == 'History':
            return
        print(f"Loading from history: {url}")
        browser = self.tabs.currentWidget().layout().itemAt(1).widget()
        browser.setUrl(QUrl(url))

    def load_custom_homepage(self):
        if os.path.exists("custom_homepage.txt"):
            return open("custom_homepage.txt").read().strip()
        return "https://www.google.com"

    def handle_download(self, download: QWebEngineDownloadItem):
        download.accept()
        download.setPath(os.path.join(os.getcwd(), download.fileName()))
        download.finished.connect(self.download_finished)
        self.downloads.append(download.fileName())
        self.show_download_manager()

    def download_finished(self):
        print("Download finished.")

    def show_download_manager(self):
        dlg = QDialog(self)
        dlg.setWindowTitle('Download Manager')
        dlg.setGeometry(200, 200, 400, 300)

        list_widget = QListWidget(dlg)
        list_widget.setGeometry(10, 10, 380, 280)

        for d in self.downloads:
            list_widget.addItem(d)

        dlg.exec_()

    def close_tab(self, index):
        widget = self.tabs.widget(index)
        if widget:
            widget.deleteLater()
        self.tabs.removeTab(index)

    def close_current_tab(self):
        index = self.tabs.currentIndex()
        if index >= 0:
            self.close_tab(index)

    def switch_tab(self, index):
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WebBrowser()
    window.show()
    sys.exit(app.exec_())

