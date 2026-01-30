#!/usr/bin/env python3
"""
AI Website Reader - PySide6 Desktop Application
Beautiful native desktop GUI for website reading and analysis
"""

import sys
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional
import threading

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QLineEdit, QPushButton, QTextEdit, QComboBox,
    QCheckBox, QSlider, QFileDialog, QMessageBox, QListWidget,
    QListWidgetItem, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QSize, QRect
from PySide6.QtGui import QFont, QColor, QPixmap, QPalette, QIcon, QTextCursor

try:
    from openai import OpenAI
except ImportError:
    print("OpenAI package required. Install: pip install openai")
    sys.exit(1)


class WorkerThread(QThread):
    """Worker thread for long-running operations"""
    finished = Signal(str)
    error = Signal(str)
    progress = Signal(str)
    
    def __init__(self, task_type, url, query=None, content=None, client=None, model="gpt-3.5-turbo", max_length=500):
        super().__init__()
        self.task_type = task_type
        self.url = url
        self.query = query
        self.content = content
        self.client = client
        self.model = model
        self.max_length = max_length
    
    def run(self):
        try:
            if self.task_type == "fetch":
                result = self._fetch_website()
            elif self.task_type == "summarize":
                result = self._summarize()
            elif self.task_type == "analyze":
                result = self._analyze()
            elif self.task_type == "tts":
                result = self._text_to_speech()
            
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
    
    def _text_to_speech(self):
        """Convert text to speech"""
        tts_text = self.content[:3000]
        response = self.client.audio.speech.create(
            model="tts-1",
            voice=self.model,  # self.model contains voice name for TTS
            input=tts_text
        )
        
        # Save audio file
        audio_filename = f"audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        audio_path = os.path.join(os.getcwd(), audio_filename)
        response.stream_to_file(audio_path)
        return audio_path
    
    def _fetch_website(self):
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(self.url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    
    def _summarize(self):
        content = self.content[:4000]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Вы полезный помощник, который кратко и точно резюмирует содержимое веб-сайтов на русском и английском языке."
                },
                {
                    "role": "user",
                    "content": f"Пожалуйста, резюмируйте следующее содержимое в {self.max_length} символов или меньше:\n\n{content}"
                }
            ],
            temperature=0.7,
            max_tokens=300
        )
        return response.choices[0].message.content
    
    def _analyze(self):
        content = self.content[:4000]
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Вы полезный помощник, который отвечает на вопросы о содержимом веб-сайтов. Отвечайте на русском языке."
                },
                {
                    "role": "user",
                    "content": f"На основе следующего содержимого веб-сайта ответьте на этот вопрос: {self.query}\n\nСодержимое:\n{content}"
                }
            ],
            temperature=0.7,
            max_tokens=400
        )
        return response.choices[0].message.content


class AIWebsiteReaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🤖 AI Website Reader v2.0")
        self.setGeometry(100, 100, 1400, 850)
        self.setMinimumSize(1200, 750)
        
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.client = None
        self.current_text = ""
        self.current_title = ""
        self.current_url = ""
        self.history = []
        self.worker_thread = None
        self.audio_file_path = None
        self.selected_voice = "alloy"
        
        self.setup_styles()
        self.setup_ui()
        self.setup_connections()
    
    def setup_styles(self):
        """Setup beautiful stylesheet"""
        # Define colors
        primary = "#667eea"
        primary_dark = "#764ba2"
        accent = "#667eea"
        bg = "#f5f7fa"
        text_dark = "#2c3e50"
        text_light = "#666"
        border_color = "#e0e0e0"
        
        style = f"""
        QMainWindow {{
            background-color: {bg};
        }}
        
        QWidget {{
            background-color: {bg};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {border_color};
            background-color: white;
        }}
        
        QTabBar::tab {{
            background-color: #e8eef7;
            color: {primary};
            padding: 10px 25px;
            border: none;
            font-weight: bold;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        
        QTabBar::tab:selected {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {primary}, stop:1 {primary_dark});
            color: white;
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: #d8dff5;
        }}
        
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {primary}, stop:1 {primary_dark});
            color: white;
            border: none;
            border-radius: 6px;
            padding: 10px 24px;
            font-weight: bold;
            font-size: 11pt;
            min-height: 35px;
        }}
        
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7a8aef, stop:1 #8456b1);
        }}
        
        QPushButton:pressed {{
            padding: 11px 23px;
        }}
        
        QPushButton:disabled {{
            background-color: #ccc;
            color: #999;
        }}
        
        QLineEdit {{
            border: 2px solid {primary};
            border-radius: 6px;
            padding: 8px 12px;
            background-color: white;
            font-size: 10pt;
            color: {text_dark};
        }}
        
        QLineEdit:focus {{
            border: 2px solid {primary_dark};
            background-color: #f8f9fa;
        }}
        
        QTextEdit {{
            border: 2px solid {border_color};
            border-radius: 6px;
            padding: 10px;
            background-color: white;
            font-size: 10pt;
            font-family: 'Courier New';
            color: {text_dark};
        }}
        
        QTextEdit:focus {{
            border: 2px solid {primary};
        }}
        
        QComboBox {{
            border: 2px solid {primary};
            border-radius: 6px;
            padding: 8px 12px;
            background-color: white;
            font-size: 10pt;
            color: {text_dark};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
        }}
        
        QCheckBox {{
            color: {text_dark};
            spacing: 8px;
            font-size: 10pt;
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {primary};
            border-radius: 4px;
            background-color: white;
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {primary};
        }}
        
        QLabel {{
            color: {text_dark};
        }}
        
        QSlider::groove:horizontal {{
            border: 1px solid {border_color};
            height: 8px;
            background: #f0f0f0;
            border-radius: 4px;
        }}
        
        QSlider::handle:horizontal {{
            background: {primary};
            border: none;
            width: 20px;
            margin: -6px 0;
            border-radius: 10px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background: {primary_dark};
        }}
        
        QListWidget {{
            border: 1px solid {border_color};
            border-radius: 6px;
            background-color: white;
            outline: none;
        }}
        
        QListWidget::item:selected {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {primary}, stop:1 {primary_dark});
            color: white;
        }}
        
        QScrollBar:vertical {{
            border: none;
            background: #f0f0f0;
            width: 10px;
            border-radius: 5px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {primary};
            border-radius: 5px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {primary_dark};
        }}
        """
        
        self.setStyleSheet(style)
    
    def setup_ui(self):
        """Setup main UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = self.create_sidebar()
        sidebar.setMinimumWidth(280)
        sidebar.setMaximumWidth(320)
        sidebar.setStyleSheet("border-right: 1px solid #e0e0e0;")
        
        # Main content
        tabs = QTabWidget()
        tabs.addTab(self.create_summarize_tab(), "📋 Резюме")
        tabs.addTab(self.create_analyze_tab(), "❓ Анализ")
        tabs.addTab(self.create_extract_tab(), "📄 Текст")
        tabs.addTab(self.create_tts_tab(), "🎙️ Озвучивание")
        tabs.addTab(self.create_history_tab(), "📊 История")
        tabs.addTab(self.create_help_tab(), "ℹ️ Справка")
        
        main_layout.addWidget(sidebar)
        main_layout.addWidget(tabs, 1)
    
    def create_sidebar(self):
        """Create settings sidebar"""
        frame = QFrame()
        frame.setStyleSheet("QFrame { background-color: white; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("⚙️ НАСТРОЙКИ")
        header_font = QFont("Segoe UI", 13, QFont.Weight.Bold)
        header.setFont(header_font)
        header.setStyleSheet("color: #667eea; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(sep1)
        
        # API Key section
        api_label = QLabel("🔑 OpenAI API Key:")
        api_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(api_label)
        
        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_input.setText(self.api_key)
        self.api_input.textChanged.connect(self.on_api_key_changed)
        self.api_input.setMinimumHeight(35)
        layout.addWidget(self.api_input)
        
        layout.addSpacing(15)
        
        # Settings section
        settings_label = QLabel("🎨 ПАРАМЕТРЫ:")
        settings_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(settings_label)
        
        self.js_checkbox = QCheckBox("🔄 JavaScript рендеринг")
        self.js_checkbox.setChecked(True)
        self.js_checkbox.setMinimumHeight(25)
        layout.addWidget(self.js_checkbox)
        
        self.tts_checkbox = QCheckBox("🔊 Текст в речь (TTS)")
        self.tts_checkbox.setChecked(False)
        self.tts_checkbox.setMinimumHeight(25)
        layout.addWidget(self.tts_checkbox)
        
        layout.addSpacing(15)
        
        # Model section
        model_label = QLabel("🧠 Модель ИИ:")
        model_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-3.5-turbo", "gpt-4"])
        self.model_combo.setMinimumHeight(35)
        layout.addWidget(self.model_combo)
        
        layout.addSpacing(15)
        
        # Length slider
        length_label = QLabel("📏 Длина резюме:")
        length_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(length_label)
        
        self.length_slider = QSlider(Qt.Orientation.Horizontal)
        self.length_slider.setMinimum(100)
        self.length_slider.setMaximum(1000)
        self.length_slider.setValue(500)
        self.length_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.length_slider.setMinimumHeight(40)
        layout.addWidget(self.length_slider)
        
        self.length_value = QLabel("500 символов")
        self.length_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.length_value.setStyleSheet("color: #666; font-weight: bold;")
        self.length_slider.valueChanged.connect(lambda v: self.length_value.setText(f"{v} символов"))
        layout.addWidget(self.length_value)
        
        layout.addStretch()
        
        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("color: #e0e0e0;")
        layout.addWidget(sep2)
        
        # Info box
        info = QLabel("💡 Совет:\nСохраняйте API\nключ в переменной\nокружения\nOPENAI_API_KEY")
        info.setFont(QFont("Segoe UI", 9))
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("background-color: #f0f0f0; padding: 12px; border-radius: 6px; color: #666;")
        info.setMinimumHeight(100)
        layout.addWidget(info)
        
        # Exit button
        exit_btn = QPushButton("❌ Выход")
        exit_btn.setMinimumHeight(40)
        exit_btn.clicked.connect(self.close)
        layout.addWidget(exit_btn)
        
        return frame
    
    def create_summarize_tab(self):
        """Create summarize tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("📋 Резюмирование сайта")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)
        
        # URL input
        url_label = QLabel("🌐 URL:")
        url_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(url_label)
        
        self.url_input_summarize = QLineEdit()
        self.url_input_summarize.setPlaceholderText("https://example.com")
        self.url_input_summarize.setMinimumHeight(38)
        layout.addWidget(self.url_input_summarize)
        
        # Button
        self.summarize_btn = QPushButton("🚀 Анализировать")
        self.summarize_btn.setMinimumHeight(45)
        self.summarize_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(self.summarize_btn)
        
        layout.addSpacing(10)
        
        # Metrics
        self.summarize_metrics = QLabel("Результаты появятся здесь...")
        self.summarize_metrics.setFont(QFont("Segoe UI", 9))
        self.summarize_metrics.setStyleSheet("color: #666;")
        layout.addWidget(self.summarize_metrics)
        
        # Results
        self.summarize_result = QTextEdit()
        self.summarize_result.setReadOnly(True)
        self.summarize_result.setMinimumHeight(350)
        layout.addWidget(self.summarize_result)
        
        # Status
        self.summarize_status = QLabel("✅ Готово")
        self.summarize_status.setFont(QFont("Segoe UI", 9))
        self.summarize_status.setStyleSheet("color: #28a745;")
        layout.addWidget(self.summarize_status)
        
        return widget
    
    def create_analyze_tab(self):
        """Create analyze tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("❓ Анализ с вопросом")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)
        
        # URL input
        url_label = QLabel("🌐 URL:")
        url_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(url_label)
        
        self.url_input_analyze = QLineEdit()
        self.url_input_analyze.setPlaceholderText("https://example.com")
        self.url_input_analyze.setMinimumHeight(38)
        layout.addWidget(self.url_input_analyze)
        
        # Question input
        question_label = QLabel("❓ Вопрос:")
        question_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(question_label)
        
        self.question_input = QTextEdit()
        self.question_input.setPlaceholderText("Например: Какие основные преимущества компании?")
        self.question_input.setMinimumHeight(100)
        layout.addWidget(self.question_input)
        
        # Button
        self.analyze_btn = QPushButton("🔍 Проанализировать")
        self.analyze_btn.setMinimumHeight(45)
        self.analyze_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(self.analyze_btn)
        
        layout.addSpacing(10)
        
        # Results
        self.analyze_result = QTextEdit()
        self.analyze_result.setReadOnly(True)
        self.analyze_result.setMinimumHeight(300)
        layout.addWidget(self.analyze_result)
        
        # Status
        self.analyze_status = QLabel("✅ Готово")
        self.analyze_status.setFont(QFont("Segoe UI", 9))
        self.analyze_status.setStyleSheet("color: #28a745;")
        layout.addWidget(self.analyze_status)
        
        return widget
    
    def create_extract_tab(self):
        """Create extract text tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("📄 Извлечение текста")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)
        
        # URL input
        url_label = QLabel("🌐 URL:")
        url_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(url_label)
        
        self.url_input_extract = QLineEdit()
        self.url_input_extract.setPlaceholderText("https://example.com")
        self.url_input_extract.setMinimumHeight(38)
        layout.addWidget(self.url_input_extract)
        
        # Button
        self.extract_btn = QPushButton("📥 Извлечь текст")
        self.extract_btn.setMinimumHeight(45)
        self.extract_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        layout.addWidget(self.extract_btn)
        
        # Metrics
        metrics_layout = QHBoxLayout()
        self.extract_chars = QLabel("📊 Символов: 0")
        self.extract_chars.setFont(QFont("Segoe UI", 9))
        self.extract_words = QLabel("📝 Слов: 0")
        self.extract_words.setFont(QFont("Segoe UI", 9))
        metrics_layout.addWidget(self.extract_chars)
        metrics_layout.addStretch()
        metrics_layout.addWidget(self.extract_words)
        layout.addLayout(metrics_layout)
        
        # Results
        self.extract_result = QTextEdit()
        self.extract_result.setReadOnly(True)
        self.extract_result.setMinimumHeight(350)
        layout.addWidget(self.extract_result)
        
        # Download button
        self.download_btn = QPushButton("⬇️ Скачать как TXT")
        self.download_btn.setMinimumHeight(40)
        layout.addWidget(self.download_btn)
        
        # Status
        self.extract_status = QLabel("✅ Готово")
        self.extract_status.setFont(QFont("Segoe UI", 9))
        self.extract_status.setStyleSheet("color: #28a745;")
        layout.addWidget(self.extract_status)
        
        return widget
    
    def create_tts_tab(self):
        """Create TTS (Text-to-Speech) tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("🎙️ Озвучивание сайта")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)
        
        # Info
        info = QLabel("Выберите голос аниме персонажа и озвучьте текст с сайта")
        info.setFont(QFont("Segoe UI", 10))
        info.setStyleSheet("color: #666;")
        layout.addWidget(info)
        
        # Voice selection
        voice_label = QLabel("🎭 Выберите голос персонажа:")
        voice_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(voice_label)
        
        # Voice buttons layout
        voice_layout = QHBoxLayout()
        
        self.voice_buttons = {}
        voices = {
            "alloy": "Астолфо\n(Мягкий)",
            "echo": "Какаши\n(Серьёзный)",
            "fishi": "Нацуки\n(Энергичный)",
            "onyx": "Итачи\n(Загадочный)",
            "nova": "Микаса\n(Стойкая)",
            "shimmer": "Рем\n(Нежная)"
        }
        
        self.selected_voice = "alloy"
        
        for voice_id, char_name in voices.items():
            btn = QPushButton(f"🎤 {char_name}")
            btn.setMinimumHeight(60)
            btn.setMinimumWidth(100)
            btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            btn.setCheckable(True)
            if voice_id == "alloy":
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, v=voice_id: self.select_voice(v))
            self.voice_buttons[voice_id] = btn
            voice_layout.addWidget(btn)
        
        layout.addLayout(voice_layout)
        
        layout.addSpacing(15)
        
        # Text input
        text_label = QLabel("📝 Текст для озвучивания:")
        text_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(text_label)
        
        self.tts_text_input = QTextEdit()
        self.tts_text_input.setPlaceholderText("Введите текст или загрузите из резюме сайта...")
        self.tts_text_input.setMinimumHeight(150)
        layout.addWidget(self.tts_text_input)
        
        # Load buttons
        load_layout = QHBoxLayout()
        
        self.load_summary_btn = QPushButton("📋 Загрузить из Резюме")
        self.load_summary_btn.setMinimumHeight(38)
        self.load_summary_btn.clicked.connect(self.load_summary_to_tts)
        load_layout.addWidget(self.load_summary_btn)
        
        self.load_extract_btn = QPushButton("📄 Загрузить из Текста")
        self.load_extract_btn.setMinimumHeight(38)
        self.load_extract_btn.clicked.connect(self.load_extract_to_tts)
        load_layout.addWidget(self.load_extract_btn)
        
        layout.addLayout(load_layout)
        
        # TTS button
        self.tts_btn = QPushButton("🔊 Озвучить текст")
        self.tts_btn.setMinimumHeight(45)
        self.tts_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.tts_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: bold;
                font-size: 11pt;
                min-height: 45px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7a8aef, stop:1 #8456b1);
            }
        """)
        self.tts_btn.clicked.connect(self.on_tts_clicked)
        layout.addWidget(self.tts_btn)
        
        layout.addSpacing(10)
        
        # Audio player
        self.audio_label = QLabel("🎵 Аудио плеер:")
        self.audio_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.audio_label)
        
        self.audio_output = QTextEdit()
        self.audio_output.setReadOnly(True)
        self.audio_output.setMaximumHeight(80)
        self.audio_output.setText("Аудио появится здесь после генерации...")
        self.audio_output.setStyleSheet("color: #666;")
        layout.addWidget(self.audio_output)
        
        # Play button
        self.play_audio_btn = QPushButton("▶️ Воспроизвести аудио")
        self.play_audio_btn.setMinimumHeight(40)
        self.play_audio_btn.setEnabled(False)
        self.play_audio_btn.clicked.connect(self.play_audio)
        layout.addWidget(self.play_audio_btn)
        
        # Download audio button
        self.download_audio_btn = QPushButton("⬇️ Скачать аудио")
        self.download_audio_btn.setMinimumHeight(40)
        self.download_audio_btn.setEnabled(False)
        self.download_audio_btn.clicked.connect(self.download_audio)
        layout.addWidget(self.download_audio_btn)
        
        # Status
        self.tts_status = QLabel("✅ Готово")
        self.tts_status.setFont(QFont("Segoe UI", 9))
        self.tts_status.setStyleSheet("color: #28a745;")
        layout.addWidget(self.tts_status)
        
        layout.addStretch()
        
        return widget
    
    def create_history_tab(self):
        """Create history tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("📊 История анализов")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)
        
        # History list
        self.history_list = QListWidget()
        self.history_list.setMinimumHeight(400)
        layout.addWidget(self.history_list)
        
        # Clear button
        self.clear_history_btn = QPushButton("🗑️ Очистить историю")
        self.clear_history_btn.setMinimumHeight(40)
        layout.addWidget(self.clear_history_btn)
        
        return widget
    
    def create_help_tab(self):
        """Create help tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        # Title
        title = QLabel("ℹ️ Справка и инструкции")
        title_font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        title.setFont(title_font)
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)
        
        # Help text
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_content = """
🚀 КАК ИСПОЛЬЗОВАТЬ AI WEBSITE READER?

1️⃣ РЕЗЮМИРОВАНИЕ
   • Введите URL сайта
   • Нажмите "Анализировать"
   • Получите краткое резюме содержимого

2️⃣ АНАЛИЗ С ВОПРОСОМ
   • Введите URL и задайте вопрос
   • ИИ найдет ответ в содержимом сайта
   • Используется для поиска конкретной информации

3️⃣ ИЗВЛЕЧЕНИЕ ТЕКСТА
   • Извлекает чистый текст со страницы
   • Удаляет весь HTML и скрипты
   • Можно скачать как текстовый файл

⚙️ НАСТРОЙКИ
   • JavaScript рендеринг: Для сайтов с динамическим контентом
   • Текст в речь: Преобразует результаты в аудио
   • Модель ИИ: Выберите между GPT-3.5 и GPT-4
   • Длина резюме: Регулируйте максимальную длину результатов

💡 СОВЕТЫ
   • Убедитесь, что у вас активный OpenAI API key
   • Для лучших результатов используйте GPT-4
   • Текст-в-речь работает только с английским голосом
   • История сохраняется для всех анализов в текущей сессии

🎨 ИНТЕРФЕЙС
   • Боковая панель содержит все основные настройки
   • Вкладки позволяют быстро переключаться между задачами
   • Результаты отображаются в реальном времени

---
Разработано с ❤️ для умного веб-анализа
        """
        help_text.setText(help_content)
        layout.addWidget(help_text)
        
        return widget
    
    def setup_connections(self):
        """Setup signal connections"""
        self.summarize_btn.clicked.connect(self.on_summarize_clicked)
        self.analyze_btn.clicked.connect(self.on_analyze_clicked)
        self.extract_btn.clicked.connect(self.on_extract_clicked)
        self.download_btn.clicked.connect(self.on_download_clicked)
        self.clear_history_btn.clicked.connect(self.on_clear_history_clicked)
    
    def on_api_key_changed(self):
        """Update API key"""
        self.api_key = self.api_input.text()
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                self.show_error("Ошибка API", str(e))
    
    def extract_text(self, html_content):
        """Extract text from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        return text
    
    def get_title(self, html_content):
        """Extract title from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.find('title')
        return title.string if title else "Неизвестный сайт"
    
    def on_summarize_clicked(self):
        """Handle summarize button click"""
        if not self.api_key:
            self.show_error("Ошибка", "Введите OpenAI API Key")
            return
        
        url = self.url_input_summarize.text().strip()
        if not url:
            self.show_error("Ошибка", "Введите URL сайта")
            return
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        self.summarize_status.setText("⏳ Загружаю сайт...")
        self.summarize_status.setStyleSheet("color: #ffc107;")
        self.summarize_btn.setEnabled(False)
        
        self.current_url = url
        
        # Clean up old thread if exists
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        
        self.worker_thread = WorkerThread("fetch", url, client=self.client)
        self.worker_thread.finished.connect(lambda html: self.on_website_fetched(html, "summarize"))
        self.worker_thread.error.connect(lambda err: self.on_worker_error(err, "summarize"))
        self.worker_thread.start()
    
    def on_analyze_clicked(self):
        """Handle analyze button click"""
        if not self.api_key:
            self.show_error("Ошибка", "Введите OpenAI API Key")
            return
        
        url = self.url_input_analyze.text().strip()
        query = self.question_input.toPlainText().strip()
        
        if not url or not query:
            self.show_error("Ошибка", "Введите URL и вопрос")
            return
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        self.analyze_status.setText("⏳ Загружаю сайт...")
        self.analyze_status.setStyleSheet("color: #ffc107;")
        self.analyze_btn.setEnabled(False)
        
        self.current_url = url
        
        # Clean up old thread if exists
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        
        self.worker_thread = WorkerThread("fetch", url, query=query, client=self.client)
        self.worker_thread.finished.connect(lambda html: self.on_website_fetched(html, "analyze"))
        self.worker_thread.error.connect(lambda err: self.on_worker_error(err, "analyze"))
        self.worker_thread.start()
    
    def on_extract_clicked(self):
        """Handle extract button click"""
        url = self.url_input_extract.text().strip()
        if not url:
            self.show_error("Ошибка", "Введите URL сайта")
            return
        
        if not url.startswith('http'):
            url = 'https://' + url
        
        self.extract_status.setText("⏳ Загружаю сайт...")
        self.extract_status.setStyleSheet("color: #ffc107;")
        self.extract_btn.setEnabled(False)
        
        self.current_url = url
        
        # Clean up old thread if exists
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        
        self.worker_thread = WorkerThread("fetch", url, client=self.client)
        self.worker_thread.finished.connect(lambda html: self.on_website_fetched(html, "extract"))
        self.worker_thread.error.connect(lambda err: self.on_worker_error(err, "extract"))
        self.worker_thread.start()
    
    def on_website_fetched(self, html, task_type):
        """Handle website fetch completion"""
        try:
            self.current_text = self.extract_text(html)
            self.current_title = self.get_title(html)
            
            if task_type == "summarize":
                self.summarize_status.setText("⏳ ИИ анализирует содержимое...")
                self.summarize_status.setStyleSheet("color: #ffc107;")
                
                # Clean up old thread
                if self.worker_thread:
                    self.worker_thread.quit()
                    self.worker_thread.wait()
                
                self.worker_thread = WorkerThread(
                    "summarize", 
                    self.current_url, 
                    content=self.current_text,
                    client=self.client,
                    model=self.model_combo.currentText(),
                    max_length=self.length_slider.value()
                )
                self.worker_thread.finished.connect(lambda result: self.on_summarize_complete(result))
                self.worker_thread.error.connect(lambda err: self.on_worker_error(err, "summarize"))
                self.worker_thread.start()
            
            elif task_type == "analyze":
                self.analyze_status.setText("⏳ ИИ отвечает на вопрос...")
                self.analyze_status.setStyleSheet("color: #ffc107;")
                
                # Clean up old thread
                if self.worker_thread:
                    self.worker_thread.quit()
                    self.worker_thread.wait()
                
                self.worker_thread = WorkerThread(
                    "analyze",
                    self.current_url,
                    query=self.question_input.toPlainText(),
                    content=self.current_text,
                    client=self.client,
                    model=self.model_combo.currentText()
                )
                self.worker_thread.finished.connect(lambda result: self.on_analyze_complete(result))
                self.worker_thread.error.connect(lambda err: self.on_worker_error(err, "analyze"))
                self.worker_thread.start()
            
            elif task_type == "extract":
                self.extract_result.setText(self.current_text)
                self.extract_chars.setText(f"📊 Символов: {len(self.current_text)}")
                self.extract_words.setText(f"📝 Слов: {len(self.current_text.split())}")
                self.extract_status.setText("✅ Текст извлечен")
                self.extract_status.setStyleSheet("color: #28a745;")
                self.extract_btn.setEnabled(True)
        
        except Exception as e:
            self.show_error("Ошибка обработки", str(e))
    
    def on_summarize_complete(self, result):
        """Handle summarize completion"""
        self.summarize_result.setText(result)
        self.summarize_metrics.setText(f"📄 {self.current_title} | 📊 {len(self.current_text)} символов")
        self.summarize_status.setText("✅ Резюме готово")
        self.summarize_status.setStyleSheet("color: #28a745;")
        self.summarize_btn.setEnabled(True)
        
        self.history.append({
            "type": "Резюме",
            "title": self.current_title,
            "result": result,
            "time": datetime.now()
        })
        self.update_history_list()
    
    def on_analyze_complete(self, result):
        """Handle analyze completion"""
        self.analyze_result.setText(result)
        self.analyze_status.setText("✅ Анализ завершен")
        self.analyze_status.setStyleSheet("color: #28a745;")
        self.analyze_btn.setEnabled(True)
        
        self.history.append({
            "type": "Анализ",
            "title": self.current_title,
            "query": self.question_input.toPlainText(),
            "result": result,
            "time": datetime.now()
        })
        self.update_history_list()
    
    def on_worker_error(self, error, task_type):
        """Handle worker error"""
        self.show_error("Ошибка", error)
        
        if task_type == "summarize":
            self.summarize_status.setText("❌ Ошибка")
            self.summarize_status.setStyleSheet("color: #dc3545;")
            self.summarize_btn.setEnabled(True)
        elif task_type == "analyze":
            self.analyze_status.setText("❌ Ошибка")
            self.analyze_status.setStyleSheet("color: #dc3545;")
            self.analyze_btn.setEnabled(True)
        elif task_type == "extract":
            self.extract_status.setText("❌ Ошибка")
            self.extract_status.setStyleSheet("color: #dc3545;")
            self.extract_btn.setEnabled(True)
    
    def update_history_list(self):
        """Update history list widget"""
        self.history_list.clear()
        for i, item in enumerate(reversed(self.history), 1):
            time_str = item["time"].strftime("%H:%M:%S")
            text = f"#{i} {item['type']} - {item['title']} ({time_str})"
            self.history_list.addItem(text)
    
    def on_download_clicked(self):
        """Handle download button click"""
        if not self.current_text:
            self.show_error("Ошибка", "Сначала извлеките текст")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить текст",
            f"{self.current_title.replace(' ', '_')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.current_text)
                self.show_info("Успех", f"Файл сохранен:\n{filename}")
            except Exception as e:
                self.show_error("Ошибка сохранения", str(e))
    
    def on_clear_history_clicked(self):
        """Clear history"""
        reply = QMessageBox.question(
            self,
            "Очистить историю",
            "Вы уверены? Это действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.history.clear()
            self.history_list.clear()
    
    def show_error(self, title, message):
        """Show error dialog"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.exec()
    
    def show_info(self, title, message):
        """Show info dialog"""
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()


    def closeEvent(self, event):
        """Clean up threads on exit"""
        if self.worker_thread:
            self.worker_thread.quit()
            self.worker_thread.wait()
        event.accept()


    def select_voice(self, voice_id):
        """Select a voice for TTS"""
        self.selected_voice = voice_id
        # Update button states
        for v_id, btn in self.voice_buttons.items():
            btn.setChecked(v_id == voice_id)
    
    
    def load_summary_to_tts(self):
        """Load summary text to TTS"""
        text = self.summarize_result.toPlainText()
        if not text:
            self.show_error("Ошибка", "Сначала создайте резюме сайта")
            return
        self.tts_text_input.setText(text)
        self.tts_status.setText("📋 Текст загружен из резюме")
        self.tts_status.setStyleSheet("color: #667eea;")
    
    
    def load_extract_to_tts(self):
        """Load extracted text to TTS"""
        text = self.extract_result.toPlainText()
        if not text:
            self.show_error("Ошибка", "Сначала извлеките текст из сайта")
            return
        self.tts_text_input.setText(text)
        self.tts_status.setText("📄 Текст загружен из извлечения")
        self.tts_status.setStyleSheet("color: #667eea;")
    
    
    def on_tts_clicked(self):
        """Handle TTS button click"""
        if not self.api_key:
            self.show_error("Ошибка", "Введите OpenAI API Key")
            return
        
        text = self.tts_text_input.toPlainText().strip()
        if not text:
            self.show_error("Ошибка", "Введите текст для озвучивания")
            return
        
        self.tts_status.setText("⏳ Генерирую аудио...")
        self.tts_status.setStyleSheet("color: #ffc107;")
        self.tts_btn.setEnabled(False)
        
        # Create worker thread for TTS
        worker = WorkerThread(
            "tts",
            "",
            content=text,
            client=self.client,
            model=self.selected_voice
        )
        self.worker_thread = worker
        worker.finished.connect(self.on_tts_complete)
        worker.error.connect(lambda err: self.on_tts_error(err))
        worker.start()
    
    
    def on_tts_complete(self, audio_path):
        """Handle TTS completion"""
        self.audio_file_path = audio_path
        self.tts_status.setText("✅ Аудио готово!")
        self.tts_status.setStyleSheet("color: #28a745;")
        self.audio_output.setText(f"🎵 Файл: {os.path.basename(audio_path)}\n✨ Озвучивание завершено успешно!")
        self.play_audio_btn.setEnabled(True)
        self.download_audio_btn.setEnabled(True)
        self.tts_btn.setEnabled(True)
    
    
    def on_tts_error(self, error):
        """Handle TTS error"""
        self.show_error("Ошибка озвучивания", error)
        self.tts_status.setText("❌ Ошибка")
        self.tts_status.setStyleSheet("color: #dc3545;")
        self.tts_btn.setEnabled(True)
    
    
    def play_audio(self):
        """Play generated audio"""
        if not self.audio_file_path or not os.path.exists(self.audio_file_path):
            self.show_error("Ошибка", "Аудио файл не найден")
            return
        
        try:
            import platform
            if platform.system() == 'Windows':
                os.startfile(self.audio_file_path)
            elif platform.system() == 'Darwin':  # macOS
                os.system(f'open "{self.audio_file_path}"')
            else:  # Linux
                os.system(f'xdg-open "{self.audio_file_path}"')
            self.audio_output.setText(f"🔊 Воспроизведение: {os.path.basename(self.audio_file_path)}")
        except Exception as e:
            self.show_error("Ошибка воспроизведения", str(e))
    
    
    def download_audio(self):
        """Download generated audio"""
        if not self.audio_file_path or not os.path.exists(self.audio_file_path):
            self.show_error("Ошибка", "Аудио файл не найден")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить аудио",
            "audio.mp3",
            "Audio Files (*.mp3);;All Files (*)"
        )
        
        if filename:
            try:
                import shutil
                shutil.copy(self.audio_file_path, filename)
                self.show_info("Успех", f"Аудио сохранено:\n{filename}")
            except Exception as e:
                self.show_error("Ошибка сохранения", str(e))


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = AIWebsiteReaderApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
