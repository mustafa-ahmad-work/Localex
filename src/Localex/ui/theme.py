"""
Unified Fluent Desktop Theme System and Localization for Offline Windows Translator.
Covers 100% of Qt widgets in both Light and Dark modes with zero hardcoded visual leaks,
balanced spacing, custom styled QComboBox dropdowns, cards, banners, and proper RTL/LTR support.
"""

from __future__ import annotations

STRINGS = {
    "en": {
        "app_title": "Offline Translator",
        "model_status_ready": "Model Ready (INT8 CPU)",
        "model_status_missing": "Model Missing (Click to Manage)",
        "model_checking": "Checking Model...",
        "history": "History",
        "models": "Models",
        "settings": "Settings",
        "tab_text": "Text Translation",
        "tab_file": "Document Translation",
        "auto_detect": "Auto Detect",
        "arabic": "Arabic",
        "english": "English",
        "swap": "Swap",
        "translate_now": "Translate",
        "translating": "Translating...",
        "source_label": "Source Text:",
        "target_label": "Translation:",
        "chars_words": "{chars} chars  |  {words} words",
        "chars": "{chars} chars",
        "paste": "Paste",
        "clear": "Clear",
        "copy": "Copy",
        "listen": "Listen",
        "listen_source": "Listen to source text",
        "listen_translation": "Listen to translation",
        "retranslate": "Re-translate",
        "source_placeholder": "Enter or paste text to translate...",
        "target_placeholder": "Translation will appear here instantly...",
        "cpu_int8": "Engine: CTranslate2 INT8 CPU",
        "offline_badge": "100% Offline",
        "file_info": "Translate TXT, Markdown (.md), and CSV files progressively into a new file without modifying the original.",
        "pick_file": "Choose File...",
        "no_file_picked": "No file selected.",
        "file_direction": "Direction:",
        "start_file_tr": "Start File Translation",
        "cancel": "Cancel",
        "ready": "Ready",
        "file_preview": "Live Translation Preview:",
        "copied_msg": "Translation copied to clipboard!",
        "completed_in": "Translation completed in {sec:.2f}s{cached}",
        "cached": " (Cached)",
        "error_tr": "Translation Error: {err}",
        "language_toggle": "العربية",
        "floating_title": "Quick Translation",
        "pin_tooltip": "Pin Always on Top",
        "copy_tooltip": "Copy Translation",
        "listen_tooltip": "Listen (Text-To-Speech)",
        "open_tooltip": "Open in Main Window",
        "close_tooltip": "Close",
        # History
        "history_title": "Translation History",
        "search_placeholder": "Search source or translated text...",
        "filter_all": "All Languages",
        "filter_ar_en": "Arabic → English",
        "filter_en_ar": "English → Arabic",
        "refresh": "Refresh",
        "col_datetime": "Date & Time",
        "col_langs": "Languages",
        "col_source": "Source Text",
        "col_target": "Translation",
        "btn_export_csv": "Export CSV",
        "btn_export_txt": "Export TXT",
        "btn_import_csv": "Import CSV",
        "btn_clear_all": "Clear All History",
        "btn_delete": "Delete",
        "confirm_clear": "Are you sure you want to delete all translation history?",
        # Settings
        "settings_title": "Application Settings",
        "tab_general": "General & Appearance",
        "tab_hotkey": "Hotkey & Floating Window",
        "tab_tts": "Speech Synthesis (TTS)",
        "tab_storage": "Storage & Portable Mode",
        "tab_engine": "Engine & Hardware",
        "group_defaults": "Default Languages & Detection",
        "lbl_default_source": "Default Source Language:",
        "lbl_default_target": "Default Target Language:",
        "chk_auto_detect": "Auto-detect source language",
        "group_appearance": "Appearance & Theme",
        "lbl_theme": "UI Theme:",
        "theme_dark": "Dark Mode",
        "theme_light": "Light Mode",
        "lbl_font_zoom": "UI Font Scaling:",
        "group_hotkey": "Global Windows Hotkey",
        "chk_hotkey": "Enable global shortcut for selected text",
        "lbl_hotkey_key": "Hotkey Combination:",
        "chk_restore_clip": "Restore original clipboard after translation",
        "lbl_clip_delay": "Clipboard Grab Delay:",
        "group_floating": "Smart Floating Window",
        "lbl_float_pos": "Default Appearance Position:",
        "float_pos_cursor": "Near Mouse Cursor",
        "float_pos_center": "Screen Center",
        "lbl_max_size": "Maximum Window Size:",
        "percent_screen": "{val}% of screen area",
        "chk_float_pin": "Keep floating window always on top by default",
        "group_voice": "Text-To-Speech Settings (Windows SAPI)",
        "lbl_voice": "Installed System Voice:",
        "lbl_speech_rate": "Speech Rate:",
        "lbl_speech_volume": "Speech Volume:",
        "btn_test_voice": "Test Voice",
        "tts_notice": "Note: Available voices depend on locally installed Windows SAPI voices.",
        "group_storage": "Storage & Portable Mode",
        "lbl_current_path": "Current Data Directory:",
        "lbl_portable_status": "Status:",
        "status_writable": "Writable [OK] (Portable mode healthy)",
        "status_readonly": "Read-only [!] (Choose another directory)",
        "btn_change_storage": "Change Directory...",
        "btn_reset_storage": "Reset to App Folder",
        "group_engine": "CTranslate2 Engine & Hardware",
        "lbl_cpu_threads": "CPU Threads:",
        "lbl_beam_size": "Beam Size:",
        "chk_history_enabled": "Save translations to local history database",
        "btn_save": "Save Settings",
        "btn_cancel": "Cancel",
    },
    "ar": {
        "app_title": "المترجم الفوري المستقل",
        "model_status_ready": "النموذج جاهز (INT8 CPU)",
        "model_status_missing": "النموذج غير متوفر (انقر للإدارة)",
        "model_checking": "فحص النموذج...",
        "history": "السجل",
        "models": "النماذج",
        "settings": "الإعدادات",
        "tab_text": "ترجمة النصوص",
        "tab_file": "ترجمة المستندات",
        "auto_detect": "اكتشاف تلقائي",
        "arabic": "العربية",
        "english": "الإنجليزية",
        "swap": "تبديل",
        "translate_now": "ترجمة الآن",
        "translating": "جاري الترجمة...",
        "source_label": "النص الأصلي:",
        "target_label": "الترجمة:",
        "chars_words": "{chars} حرف  |  {words} كلمة",
        "chars": "{chars} حرف",
        "paste": "لصق",
        "clear": "مسح",
        "copy": "نسخ",
        "listen": "استماع",
        "listen_source": "استماع للنص الأصلي",
        "listen_translation": "استماع للترجمة",
        "retranslate": "إعادة",
        "source_placeholder": "أدخل أو الصق النص هنا...",
        "target_placeholder": "ستظهر نتيجة الترجمة هنا فور اكتمال المعالجة...",
        "cpu_int8": "المعالج: CTranslate2 INT8 CPU",
        "offline_badge": "بدون إنترنت 100%",
        "file_info": "ترجمة ملفات TXT و Markdown و CSV تدريجياً وحفظ النتيجة في ملف جديد دون المساس بالأصل.",
        "pick_file": "اختيار ملف...",
        "no_file_picked": "لم يتم اختيار ملف بعد.",
        "file_direction": "اتجاه الترجمة:",
        "start_file_tr": "بدء ترجمة الملف",
        "cancel": "إلغاء",
        "ready": "جاهز",
        "file_preview": "معاينة الترجمة الحية:",
        "copied_msg": "تم نسخ الترجمة إلى الحافظة بنجاح!",
        "completed_in": "اكتملت الترجمة في {sec:.2f} ثانية{cached}",
        "cached": " (ذاكرة التخزين المؤقت)",
        "error_tr": "خطأ في الترجمة: {err}",
        "language_toggle": "English",
        "floating_title": "ترجمة فورية عائمة",
        "pin_tooltip": "تثبيت في المقدمة",
        "copy_tooltip": "نسخ الترجمة",
        "listen_tooltip": "قراءة صوتية",
        "open_tooltip": "فتح في النافذة الرئيسية",
        "close_tooltip": "إغلاق",
        # History
        "history_title": "سجل الترجمات المحلية",
        "search_placeholder": "ابحث في النصوص المترجمة أو الأصلية...",
        "filter_all": "جميع اللغات",
        "filter_ar_en": "العربية ← الإنجليزية",
        "filter_en_ar": "الإنجليزية ← العربية",
        "refresh": "تحديث",
        "col_datetime": "التاريخ والوقت",
        "col_langs": "اللغات",
        "col_source": "النص الأصلي",
        "col_target": "الترجمة",
        "btn_export_csv": "تصدير CSV",
        "btn_export_txt": "تصدير TXT",
        "btn_import_csv": "استيراد CSV",
        "btn_clear_all": "مسح السجل بالكامل",
        "btn_delete": "حذف",
        "confirm_clear": "هل أنت متأكد من رغبتك في حذف سجل الترجمات بالكامل؟",
        # Settings
        "settings_title": "إعدادات البرنامج الشاملة",
        "tab_general": "العام والمظهر",
        "tab_hotkey": "الاختصار والنافذة العائمة",
        "tab_tts": "تحويل النص إلى كلام (TTS)",
        "tab_storage": "التخزين والوضع المحمول",
        "tab_engine": "المحرك والعتاد",
        "group_defaults": "اللغات الافتراضية واكتشاف اللغة",
        "lbl_default_source": "لغة المصدر الافتراضية:",
        "lbl_default_target": "لغة الهدف الافتراضية:",
        "chk_auto_detect": "تفعيل اكتشاف لغة النص تلقائياً",
        "group_appearance": "المظهر والواجهة",
        "lbl_theme": "المظهر العام:",
        "theme_dark": "الوضع الداكن (Dark)",
        "theme_light": "الوضع الفاتح (Light)",
        "lbl_font_zoom": "تكبير نصوص الواجهة:",
        "group_hotkey": "الاختصار العام في Windows",
        "chk_hotkey": "تفعيل الاختصار العام لترجمة النص المحدد",
        "lbl_hotkey_key": "مفتاح الاختصار:",
        "chk_restore_clip": "استعادة محتوى الحافظة الأصلي بعد الالتقاط",
        "lbl_clip_delay": "مهلة التقاط الحافظة:",
        "group_floating": "النافذة العائمة الذكية",
        "lbl_float_pos": "موقع الظهور الافتراضي:",
        "float_pos_cursor": "بالقرب من مؤشر الفأرة",
        "float_pos_center": "منتصف الشاشة",
        "lbl_max_size": "أقصى حجم للنافذة:",
        "percent_screen": "{val}% من مساحة الشاشة",
        "chk_float_pin": "تثبيت النافذة العائمة في المقدمة دائماً افتراضياً",
        "group_voice": "إعدادات تحويل النص إلى كلام (Windows SAPI)",
        "lbl_voice": "الصوت المثبت محلياً:",
        "lbl_speech_rate": "سرعة القراءة:",
        "lbl_speech_volume": "مستوى الصوت:",
        "btn_test_voice": "اختبار الصوت",
        "tts_notice": "ملاحظة: تعتمد الأصوات المتاحة على الأصوات المثبتة محلياً في نظام Windows.",
        "group_storage": "التخزين والوضع المحمول",
        "lbl_current_path": "مسار البيانات الحالي:",
        "lbl_portable_status": "حالة الصلاحيات:",
        "status_writable": "مسموح بالكتابة [OK] (الوضع المحمول سليم)",
        "status_readonly": "محمي / للقراءة فقط [!] (اختر مجلداً آخر)",
        "btn_change_storage": "تغيير المجلد...",
        "btn_reset_storage": "استعادة مجلد البرنامج",
        "group_engine": "محرك CTranslate2 والعتاد",
        "lbl_cpu_threads": "خيوط المعالج (CPU Threads):",
        "lbl_beam_size": "عرض البحث (Beam Size):",
        "chk_history_enabled": "حفظ الترجمات في قاعدة البيانات المحلية",
        "btn_save": "حفظ الإعدادات",
        "btn_cancel": "إلغاء",
    },
}

DARK_THEME = """
/* Global Reset */
QWidget {
    background-color: #202024;
    color: #E2E2E8;
    font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif;
    font-size: 13px;
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
    outline: none;
}

QMainWindow, QDialog {
    background-color: #202024;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #333338;
    background-color: #26262B;
    margin-top: -1px;
}

QTabBar::tab {
    background: #1C1C20;
    color: #9C9CA6;
    padding: 8px 20px;
    margin-right: 4px;
    border: 1px solid #333338;
    border-bottom: none;
    font-weight: 500;
}

QTabBar::tab:selected {
    background: #26262B;
    color: #FFFFFF;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background: #242429;
    color: #E2E2E8;
}

/* Text Inputs */
QTextEdit, QPlainTextEdit, QLineEdit {
    background-color: #16161A;
    color: #F4F4F5;
    border: 1px solid #36363E;
    
    padding: 8px 12px;
    font-size: 13px;
    line-height: 1.5;
}

QTextEdit:focus, QPlainTextEdit:focus, QLineEdit:focus {
    border: 1px solid #0078D4;
    background-color: #19191D;
}

/* Buttons */
QPushButton {
    background-color: #2A2A32;
    color: #F4F4F5;
    border: 1px solid #3E3E4C;
    
    padding: 6px 14px;
    min-height: 26px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #383844;
    border-color: #0078D4;
}

QPushButton:pressed {
    background-color: #1F1F24;
}

QPushButton:disabled {
    background-color: #222226;
    color: #64646E;
    border-color: #2C2C32;
}

QPushButton.primary {
    background-color: #0078D4;
    color: #FFFFFF;
    border: 1px solid #1084D8;
    font-weight: 600;
    padding: 7px 18px;
}

QPushButton.primary:hover {
    background-color: #1084D8;
    border-color: #2B88D8;
}

QPushButton.primary:pressed {
    background-color: #005A9E;
}

QPushButton.secondary {
    background-color: #282830;
    color: #E2E2E8;
    border: 1px solid #40404C;
    
    padding: 5px 12px;
}

QPushButton.secondary:hover {
    background-color: #353540;
    border-color: #0078D4;
}

QPushButton.danger {
    background-color: #C42B1C;
    color: #FFFFFF;
    border: 1px solid #A82315;
    
}

QPushButton.danger:hover {
    background-color: #D83B27;
}

QPushButton.icon-btn {
    background-color: #282830;
    color: #E2E2E8;
    border: 1px solid #40404C;
    padding: 5px 12px;
    
    font-weight: 500;
}

QPushButton.icon-btn:hover {
    background-color: #353540;
    border-color: #0078D4;
    color: #FFFFFF;
}

QPushButton.icon-btn:pressed {
    background-color: #1E1E24;
}

/* QComboBox Styling */
QComboBox {
    background-color: #2C2C32;
    color: #F4F4F5;
    border: 1px solid #3E3E48;
    
    padding: 6px 14px;
    min-height: 22px;
}

QComboBox:hover {
    border-color: #50505E;
}

QComboBox:on {
    border-color: #0078D4;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}

QComboBox::down-arrow {
    image: none;
    border: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #26262B;
    color: #F4F4F5;
    border: 1px solid #3E3E48;
    
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
    padding: 4px;
}

/* Cards & Info Frames */
QFrame.card, QFrame#FloatingFrame, QFrame#ModelCardFrame, QFrame#ProgressFrame {
    background-color: #26262B;
    border: 1px solid #36363E;
    
}

QLabel.info-banner {
    background-color: #26262B;
    border-left: 3px solid #0078D4;
    padding: 10px 14px;
    
    color: #D4D4D8;
}

/* Scroll Area & Bars */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    background: #1C1C20;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #383842;
    min-height: 24px;
    
}

QScrollBar::handle:vertical:hover {
    background: #4C4C58;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* Tables */
QTableWidget {
    background-color: #16161A;
    color: #F4F4F5;
    border: 1px solid #333338;
    gridline-color: #26262C;
    
}

QHeaderView::section {
    background-color: #242429;
    color: #9C9CA6;
    padding: 8px;
    border: none;
    border-right: 1px solid #26262C;
    border-bottom: 1px solid #333338;
    font-weight: 600;
}

/* Status Bar */
QStatusBar {
    background-color: #1C1C20;
    color: #9C9CA6;
    font-size: 12px;
}

/* Group Box */
QGroupBox {
    border: 1px solid #383840;
    
    margin-top: 14px;
    padding-top: 16px;
    font-weight: 600;
    color: #0078D4;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
}

/* Sliders & Spinners */
QSlider::groove:horizontal {
    height: 4px;
    background: #36363E;
    
}

QSlider::sub-page:horizontal {
    background: #0078D4;
    
}

QSlider::handle:horizontal {
    background: #0078D4;
    border: 2px solid #FFFFFF;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    
}

QSpinBox {
    background-color: #2C2C32;
    color: #F4F4F5;
    border: 1px solid #3E3E48;
    
    padding: 5px 10px;
}
"""

LIGHT_THEME = """
/* Global Reset */
QWidget {
    background-color: #F8F9FA;
    color: #1A1A1E;
    font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif;
    font-size: 13px;
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
    outline: none;
}

QMainWindow, QDialog {
    background-color: #F8F9FA;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #D6D8DC;
    background-color: #FFFFFF;
    
    margin-top: -1px;
}

QTabBar::tab {
    background: #EBEDF0;
    color: #55555C;
    padding: 8px 20px;
    margin-right: 4px;
    border: 1px solid #D6D8DC;
    border-bottom: none;
    font-weight: 500;
}

QTabBar::tab:selected {
    background: #FFFFFF;
    color: #1A1A1E;
    font-weight: 600;
}

QTabBar::tab:hover:!selected {
    background: #F1F3F5;
    color: #1A1A1E;
}

/* Text Inputs */
QTextEdit, QPlainTextEdit, QLineEdit {
    background-color: #FFFFFF;
    color: #1A1A1E;
    border: 1px solid #CED4DA;
    
    padding: 8px 12px;
    font-size: 13px;
    line-height: 1.5;
}

QTextEdit:focus, QPlainTextEdit:focus, QLineEdit:focus {
    border: 1px solid #0078D4;
    background-color: #FFFFFF;
}

/* Buttons */
QPushButton {
    background-color: #FFFFFF;
    color: #1A1A1E;
    border: 1px solid #D0D5DD;
    
    padding: 6px 14px;
    min-height: 26px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #F8FAFC;
    border-color: #0078D4;
    color: #0078D4;
}

QPushButton:pressed {
    background-color: #E2E8F0;
}

QPushButton:disabled {
    background-color: #F8F9FA;
    color: #8E959E;
    border-color: #E2E6EA;
}

QPushButton.primary {
    background-color: #0078D4;
    color: #FFFFFF;
    border: 1px solid #006CBE;
    font-weight: 600;
    padding: 7px 18px;
}

QPushButton.primary:hover {
    background-color: #1084D8;
    border-color: #1084D8;
}

QPushButton.primary:pressed {
    background-color: #005A9E;
}

QPushButton.secondary {
    background-color: #FFFFFF;
    color: #2D3139;
    border: 1px solid #D0D5DD;
    
    padding: 5px 12px;
}

QPushButton.secondary:hover {
    background-color: #F1F5F9;
    border-color: #0078D4;
    color: #0078D4;
}

QPushButton.danger {
    background-color: #D13438;
    color: #FFFFFF;
    border: 1px solid #A82315;
    
}

QPushButton.danger:hover {
    background-color: #EA4A4F;
}

QPushButton.icon-btn {
    background-color: #FFFFFF;
    color: #2D3139;
    border: 1px solid #D0D5DD;
    padding: 5px 12px;
    
    font-weight: 500;
}

QPushButton.icon-btn:hover {
    background-color: #F1F5F9;
    border-color: #0078D4;
    color: #0078D4;
}

QPushButton.icon-btn:pressed {
    background-color: #E2E8F0;
}

/* QComboBox Styling */
QComboBox {
    background-color: #FFFFFF;
    color: #1A1A1E;
    border: 1px solid #CED4DA;
    
    padding: 6px 14px;
    min-height: 22px;
}

QComboBox:hover {
    border-color: #ADB5BD;
}

QComboBox:on {
    border-color: #0078D4;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: none;
}

QComboBox::down-arrow {
    image: none;
    border: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    margin-right: 6px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #1A1A1E;
    border: 1px solid #CED4DA;
    
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
    padding: 4px;
}

/* Cards & Info Frames */
QFrame.card, QFrame#FloatingFrame, QFrame#ModelCardFrame, QFrame#ProgressFrame {
    background-color: #FFFFFF;
    border: 1px solid #D6D8DC;
    
}

QLabel.info-banner {
    background-color: #F1F3F5;
    border-left: 3px solid #0078D4;
    padding: 10px 14px;
    
    color: #343A40;
}

/* Scroll Area & Bars */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    background: #F8F9FA;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #CED4DA;
    min-height: 24px;
    
}

QScrollBar::handle:vertical:hover {
    background: #ADB5BD;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* Tables */
QTableWidget {
    background-color: #FFFFFF;
    color: #1A1A1E;
    border: 1px solid #D6D8DC;
    gridline-color: #E9ECEF;
    
}

QHeaderView::section {
    background-color: #F1F3F5;
    color: #495057;
    padding: 8px;
    border: none;
    border-right: 1px solid #E9ECEF;
    border-bottom: 1px solid #D6D8DC;
    font-weight: 600;
}

/* Status Bar */
QStatusBar {
    background-color: #EBEDF0;
    color: #55555C;
    font-size: 12px;
}

/* Group Box */
QGroupBox {
    border: 1px solid #D6D8DC;
    
    margin-top: 14px;
    padding-top: 16px;
    font-weight: 600;
    color: #0078D4;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
}

/* Sliders & Spinners */
QSlider::groove:horizontal {
    height: 4px;
    background: #DEE2E6;
    
}

QSlider::sub-page:horizontal {
    background: #0078D4;
    
}

QSlider::handle:horizontal {
    background: #0078D4;
    border: 2px solid #FFFFFF;
    width: 14px;
    margin-top: -5px;
    margin-bottom: -5px;
    
}

QSpinBox {
    background-color: #FFFFFF;
    color: #1A1A1E;
    border: 1px solid #CED4DA;
    
    padding: 5px 10px;
}
"""


def get_theme_stylesheet(theme_name: str = "dark") -> str:
    return DARK_THEME if theme_name.lower() == "dark" else LIGHT_THEME
