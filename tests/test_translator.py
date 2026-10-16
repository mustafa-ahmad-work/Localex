"""
Unit tests for language detection, chunking, and translator engine.
"""

import pytest
from Localex.utils import (
    chunk_text_by_paragraphs,
    detect_language,
    is_arabic_script,
    split_sentences,
)
from Localex.translator import TranslationEngine


def test_detect_language_arabic():
    text = "مرحبا بك في هذا البرنامج المتكامل"
    assert detect_language(text) == "ar"
    assert is_arabic_script(text) is True


def test_detect_language_english():
    text = "Hello, welcome to this offline translator application."
    assert detect_language(text) == "en"
    assert is_arabic_script(text) is False


def test_detect_language_mixed():
    # Mostly Arabic with some English words
    text = "هذا البرنامج يستخدم Python و CTranslate2 للترجمة السريعة"
    assert detect_language(text) == "ar"

    # Mostly English with some Arabic words
    text_en = "This software is written in Python to support العربية translation efficiently."
    assert detect_language(text_en) == "en"


def test_detect_language_empty():
    assert detect_language("") == "en"
    assert detect_language("   ") == "en"
    assert detect_language("123456 !!!") == "en"


def test_split_sentences():
    para = "This is sentence one. This is sentence two! And here is sentence three?"
    chunks = split_sentences(para, max_chars=35)
    assert len(chunks) >= 2
    # Verify that reconstructed pieces contain all sentences
    combined = " ".join(chunks)
    assert "sentence one" in combined
    assert "sentence three" in combined


def test_chunk_text_by_paragraphs_preserves_structure():
    text = "First paragraph here.\n\nSecond paragraph here with some text.\nThird paragraph."
    chunks_with_seps = chunk_text_by_paragraphs(text, max_chunk_chars=300)

    # Reconstruct text
    reconstructed = "".join([c + sep for c, sep in chunks_with_seps])
    assert reconstructed == text


def test_translator_cache():
    engine = TranslationEngine()
    # Populate cache manually
    engine._cache[("test", "en", "ar")] = "اختبار"

    result = engine.translate("test", source_lang="en", target_lang="ar")
    assert result.translated_text == "اختبار"
    assert result.is_cached is True


def test_get_text_direction_mixed_and_arabic():
    from Localex.utils import get_text_direction

    # Arabic starting with English words / terms must be detected as RTL
    assert get_text_direction("Python هي لغة برمجة قوية ومشهورة") == "rtl"
    assert get_text_direction("API: واجهة برمجة التطبيقات لتكامل الأنظمة") == "rtl"
    assert get_text_direction("Docker يتيح تشغيل الحاويات بسهولة") == "rtl"
    assert get_text_direction("1. الخطوة الأولى للبدء في البرنامج") == "rtl"
    assert get_text_direction("مرحبا بالعالم") == "rtl"

    # HTML tags / markdown must not fool direction detection
    assert get_text_direction('<div dir="ltr"><span style="color:red">مرحبا بك</span></div>') == "rtl"
    assert get_text_direction("# عنوان رئيسي باللغة العربية") == "rtl"
    assert get_text_direction("**تنبيه**: يرجى مراعاة ما يلي") == "rtl"
    assert get_text_direction("[0] تم استكمال الترجمة بنجاح") == "rtl"

    # Pure English
    assert get_text_direction("This is a clean English sentence.") == "ltr"
    assert get_text_direction("CTranslate2 is a fast inference engine.") == "ltr"


def test_set_text_edit_content_plain_and_direction():
    from PySide6.QtWidgets import QApplication, QTextEdit
    from PySide6.QtCore import Qt
    from Localex.utils import set_text_edit_content

    app = QApplication.instance() or QApplication([])
    te = QTextEdit()

    # Set Arabic text
    set_text_edit_content(te, "Python هي لغة برمجة مفتوحة المصدر")
    assert te.acceptRichText() is False
    assert te.layoutDirection() == Qt.RightToLeft
    assert bool(te.alignment() & Qt.AlignRight) is True

    # Set English text
    set_text_edit_content(te, "This is an English output")
    assert te.layoutDirection() == Qt.LeftToRight
    assert bool(te.alignment() & Qt.AlignLeft) is True


def test_ctranslate2_model_loading_no_mkl_error():
    from pathlib import Path
    model_dir = Path("models/nllb-200-distilled-600M-int8")
    if model_dir.exists():
        engine = TranslationEngine(model_path=model_dir, cpu_threads=4)
        loaded = engine.load()
        assert loaded is True
        assert engine.is_loaded is True
        engine.unload()
