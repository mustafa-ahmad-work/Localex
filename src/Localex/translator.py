"""
Offline translation engine wrapping CTranslate2 and SentencePiece for NLLB-200.
Supports INT8 CPU execution, auto language detection, paragraph-preserving batch chunking, and memory management.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Prevent Intel MKL memory allocation errors (mkl_malloc: failed to allocate memory)
os.environ.setdefault("CT2_PACKED_GEMM", "0")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import ctranslate2
import sentencepiece as spm

from Localex.model_manager import ModelManager
from Localex.utils import (
    chunk_text_by_paragraphs,
    detect_language,
    mask_special_content,
    restore_special_content,
)

logger = logging.getLogger(__name__)

# FLORES-200 Language Tag mappings
LANG_CODES: Dict[str, str] = {
    "ar": "arb_Arab",
    "en": "eng_Latn",
    "arb_Arab": "arb_Arab",
    "eng_Latn": "eng_Latn",
}

SPECIAL_TOKENS = {"arb_Arab", "eng_Latn", "</s>", "<s>", "<unk>", "<pad>"}


class TranslationError(Exception):
    """Raised when translation fails."""
    pass


class ModelNotFoundError(TranslationError):
    """Raised when the specified model files are not found."""
    pass


@dataclass
class TranslationResult:
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    model_name: str
    char_count: int
    duration_seconds: float
    is_cached: bool = False


class TranslationEngine:
    """
    Manages loading and running the CTranslate2 model and SentencePiece tokenizer.
    """

    def __init__(
        self,
        model_path: Optional[Path | str] = None,
        cpu_threads: int = 4,
        beam_size: int = 1,
        batch_size: int = 16,
    ) -> None:
        self.model_path = Path(model_path).resolve() if model_path else None
        self.cpu_threads = cpu_threads
        self.beam_size = beam_size
        self.batch_size = batch_size

        self.translator: Optional[ctranslate2.Translator] = None
        self.sp_processor: Optional[spm.SentencePieceProcessor] = None
        self._loaded_model_path: Optional[Path] = None

        # Simple in-memory translation cache (LRU-like dict)
        self._cache: Dict[Tuple[str, str, str], str] = {}
        self._cache_max_size = 200

    @property
    def is_loaded(self) -> bool:
        return self.translator is not None and self.sp_processor is not None

    def set_model_path(self, model_path: Path | str) -> None:
        new_path = Path(model_path).resolve()
        if new_path != self.model_path:
            self.unload()
            self.model_path = new_path

    def unload(self) -> None:
        """Frees the loaded model from memory."""
        import gc
        if self.translator is not None:
            del self.translator
            self.translator = None
        if self.sp_processor is not None:
            del self.sp_processor
            self.sp_processor = None
        self._loaded_model_path = None
        self._cache.clear()
        gc.collect()
        logger.info("Translation model unloaded from memory.")

    def load(self, model_path: Optional[Path | str] = None) -> bool:
        """
        Loads the CTranslate2 model and SentencePiece tokenizer into memory.
        """
        import gc
        if model_path:
            self.set_model_path(model_path)

        if not self.model_path:
            raise ModelNotFoundError("لم يتم تحديد مسار لنموذج الترجمة.")

        if not self.model_path.exists():
            raise ModelNotFoundError(f"مجلد النموذج غير موجود: {self.model_path}")

        # Check model files
        model_manager = ModelManager()
        is_valid, reason = model_manager.validate_model_directory(self.model_path)
        if not is_valid:
            raise TranslationError(f"النموذج غير صالح: {reason}")

        # Find SentencePiece model file
        spm_candidates = [
            self.model_path / "sentencepiece.bpe.model",
            self.model_path / "spm.model",
            self.model_path / "flores200_sacrebleu_tokenizer_spm.model",
            self.model_path / "source.spm",
        ]
        spm_path = next((p for p in spm_candidates if p.is_file()), None)
        if not spm_path:
            raise ModelNotFoundError(f"لم يتم العثور على ملف SentencePiece داخل {self.model_path}")

        logger.info(f"Loading SentencePiece processor from: {spm_path}")
        sp = spm.SentencePieceProcessor()
        if not sp.load(str(spm_path)):
            raise TranslationError("فشل تحميل ملف معالج الرموز SentencePiece.")
        self.sp_processor = sp

        # Clean memory before allocating model weights
        gc.collect()

        threads = max(1, self.cpu_threads)
        logger.info(
            f"Loading CTranslate2 model from {self.model_path} (INT8, inter_threads=1, intra_threads={threads})..."
        )
        try:
            self.translator = ctranslate2.Translator(
                str(self.model_path),
                device="cpu",
                compute_type="int8",
                inter_threads=1,
                intra_threads=threads,
            )
            self._loaded_model_path = self.model_path
            logger.info("CTranslate2 model loaded successfully.")
            return True
        except Exception as primary_err:
            logger.warning(
                f"Initial CTranslate2 load failed ({primary_err}). Attempting fallback with single intra_thread..."
            )
            gc.collect()
            try:
                self.translator = ctranslate2.Translator(
                    str(self.model_path),
                    device="cpu",
                    compute_type="int8",
                    inter_threads=1,
                    intra_threads=1,
                )
                self._loaded_model_path = self.model_path
                logger.info("CTranslate2 model loaded successfully in fallback mode.")
                return True
            except Exception as fallback_err:
                logger.error(f"Failed to load CTranslate2 model: {fallback_err}")
                self.unload()
                raise TranslationError(f"فشل تحميل نموذج CTranslate2: {fallback_err}")

    def translate(
        self,
        text: str,
        source_lang: str = "auto",
        target_lang: str = "ar",
    ) -> TranslationResult:
        """
        Translates the given text with auto-language detection, chunking, and paragraph reconstruction.
        """
        if not text or not text.strip():
            return TranslationResult(
                source_text=text,
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                model_name=self.model_path.name if self.model_path else "None",
                char_count=0,
                duration_seconds=0.0,
            )

        start_time = time.time()

        # Handle Language Auto-detection
        resolved_source = source_lang
        resolved_target = target_lang

        # If text contains no letters (pure numbers, whitespace, or symbols), return as-is
        if not any(c.isalpha() for c in text):
            return TranslationResult(
                source_text=text,
                translated_text=text,
                source_lang=resolved_source if resolved_source != "auto" else "en",
                target_lang=resolved_target,
                model_name="numeric_bypass",
                char_count=len(text),
                duration_seconds=0.0,
                is_cached=True,
            )

        if resolved_source == "auto":
            detected = detect_language(text)
            resolved_source = detected
            # Smart language direction: if detected source is identical to target, flip target
            if resolved_source == "ar" and resolved_target == "ar":
                resolved_target = "en"
            elif resolved_source == "en" and resolved_target == "en":
                resolved_target = "ar"

        # Check Cache
        cache_key = (text.strip(), resolved_source, resolved_target)
        if cache_key in self._cache:
            return TranslationResult(
                source_text=text,
                translated_text=self._cache[cache_key],
                source_lang=resolved_source,
                target_lang=resolved_target,
                model_name=self.model_path.name if self.model_path else "Cached",
                char_count=len(text),
                duration_seconds=time.time() - start_time,
                is_cached=True,
            )

        if not self.is_loaded:
            self.load()

        assert self.translator is not None
        assert self.sp_processor is not None

        # Mask code blocks, inline code, markdown links, raw URLs, and emails
        masked_text, masked_items = mask_special_content(text)

        src_flores = LANG_CODES.get(resolved_source, "eng_Latn")
        tgt_flores = LANG_CODES.get(resolved_target, "arb_Arab")

        # Split text into structural chunks preserving line breaks
        chunks_with_seps = chunk_text_by_paragraphs(masked_text, max_chunk_chars=400)

        # Determine which chunks actually need translation (contain letters)
        non_empty_indices = [
            i for i, (chunk, _) in enumerate(chunks_with_seps)
            if chunk.strip() and any(c.isalpha() for c in chunk)
        ]
        batch_texts = [chunks_with_seps[i][0] for i in non_empty_indices]

        # Collect any markdown link labels that need translation
        md_link_items = [
            item for item in masked_items
            if item["type"] == "md_link" and item["label"].strip() and any(c.isalpha() for c in item["label"])
        ]
        link_offset = len(batch_texts)
        for item in md_link_items:
            batch_texts.append(item["label"])

        translated_chunks_map: Dict[int, str] = {}
        translated_labels: Dict[str, str] = {}

        if batch_texts:
            # Tokenize using SentencePiece
            tokenized_batch = [self.sp_processor.encode_as_pieces(t) for t in batch_texts]

            # Prepend source language code and append end-of-sequence token
            input_tokens = [[src_flores] + tokens + ["</s>"] for tokens in tokenized_batch]
            target_prefixes = [[tgt_flores]] * len(input_tokens)

            try:
                results = self.translator.translate_batch(
                    input_tokens,
                    target_prefix=target_prefixes,
                    beam_size=self.beam_size,
                    max_batch_size=self.batch_size,
                )
            except Exception as e:
                logger.error(f"CTranslate2 inference error: {e}")
                raise TranslationError(f"حدث خطأ أثناء معالجة الترجمة: {e}")

            for i, res in enumerate(results):
                hyp_tokens = res.hypotheses[0] if res.hypotheses else []
                # Clean up target language prefix if present at start
                cleaned_tokens = [
                    tok for tok in hyp_tokens if tok not in SPECIAL_TOKENS and tok != tgt_flores
                ]
                decoded_str = self.sp_processor.decode(cleaned_tokens).strip()

                if i < link_offset:
                    chunk_idx = non_empty_indices[i]
                    translated_chunks_map[chunk_idx] = decoded_str
                else:
                    item_idx = md_link_items[i - link_offset]["index"]
                    translated_labels[item_idx] = decoded_str

        # Reconstruct output text with exact original paragraph and newline structure
        reconstructed_parts: List[str] = []
        for i, (orig_chunk, sep) in enumerate(chunks_with_seps):
            if not orig_chunk.strip():
                # Keep whitespace line
                reconstructed_parts.append(orig_chunk + sep)
            elif not any(c.isalpha() for c in orig_chunk):
                # No letters (e.g. standalone bracket placeholder, numbers, punctuation)
                reconstructed_parts.append(orig_chunk + sep)
            else:
                translated_piece = translated_chunks_map.get(i, orig_chunk)
                reconstructed_parts.append(translated_piece + sep)

        translated_text = "".join(reconstructed_parts).rstrip("\r\n")

        # Restore masked items (links, urls, code)
        translated_text = restore_special_content(translated_text, masked_items, translated_labels)

        # Save to Cache
        if len(self._cache) >= self._cache_max_size:
            # Evict oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[cache_key] = translated_text

        duration = time.time() - start_time
        return TranslationResult(
            source_text=text,
            translated_text=translated_text,
            source_lang=resolved_source,
            target_lang=resolved_target,
            model_name=self.model_path.name if self.model_path else "NLLB",
            char_count=len(text),
            duration_seconds=duration,
            is_cached=False,
        )
