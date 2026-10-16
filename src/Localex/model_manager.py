"""
Model manager for detecting, validating, cataloging, and managing offline translation models.
Supports CTranslate2 INT8 models, checks file integrity, and scans directories.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from Localex.paths import default_paths

logger = logging.getLogger(__name__)


@dataclass
class ModelFileInfo:
    filename: str
    url: str
    size_bytes: int
    sha256: Optional[str] = None
    optional: bool = False


@dataclass
class ModelCatalogItem:
    model_id: str
    name: str
    description: str
    architecture: str
    quantization: str
    required_disk_mb: int
    required_ram_mb: int
    repo_id: str
    files: List[ModelFileInfo]
    disclaimer: str = (
        "جودة الترجمة تعتمد على النموذج المستخدم. النماذج العامة ممتازة للنصوص والمقالات "
        "ولكنها قد لا تكون مثالية للمصطلحات البرمجية الدقيقة وتراكيب الأكواد البرمجية."
    )


# Official Catalog of supported models
CATALOG: Dict[str, ModelCatalogItem] = {
    "nllb-200-distilled-600M-int8": ModelCatalogItem(
        model_id="nllb-200-distilled-600M-int8",
        name="NLLB-200 Distilled 600M (INT8)",
        description="النموذج القياسي الموصى به: خفيف وسريع، يعمل بكفاءة عالية على المعالج CPU مع استهلاك منخفض للذاكرة.",
        architecture="NLLB-200 (Meta)",
        quantization="INT8",
        required_disk_mb=635,
        required_ram_mb=1200,
        repo_id="JustFrederik/nllb-200-distilled-600M-ct2-int8",
        files=[
            ModelFileInfo(
                filename="model.bin",
                url="https://huggingface.co/JustFrederik/nllb-200-distilled-600M-ct2-int8/resolve/main/model.bin",
                size_bytes=622595991,
                sha256="ed1beaf75134de7505315a5223162f56acff397eff6b50638a500d3936fe707b",
            ),
            ModelFileInfo(
                filename="sentencepiece.bpe.model",
                url="https://huggingface.co/JustFrederik/nllb-200-distilled-600M-ct2-int8/resolve/main/sentencepiece.bpe.model",
                size_bytes=4852054,
                sha256="14bb8dfb35c0ffdea7bc01e56cea38b9e3d5efcdcb9c251d6b40538e1aab555a",
            ),
            ModelFileInfo(
                filename="shared_vocabulary.txt",
                url="https://huggingface.co/JustFrederik/nllb-200-distilled-600M-ct2-int8/resolve/main/shared_vocabulary.txt",
                size_bytes=2568098,
                sha256=None,
            ),
            ModelFileInfo(
                filename="config.json",
                url="https://huggingface.co/JustFrederik/nllb-200-distilled-600M-ct2-int8/resolve/main/config.json",
                size_bytes=159,
                sha256=None,
            ),
            ModelFileInfo(
                filename="special_tokens_map.json",
                url="https://huggingface.co/JustFrederik/nllb-200-distilled-600M-ct2-int8/resolve/main/special_tokens_map.json",
                size_bytes=3548,
                optional=True,
            ),
        ],
    ),
}


class ModelStatus:
    INSTALLED = "installed"
    INCOMPLETE = "incomplete"
    NOT_DOWNLOADED = "not_downloaded"
    CORRUPTED = "corrupted"
    UNKNOWN = "unknown"


def compute_file_sha256(file_path: Path, block_size: int = 1024 * 1024) -> str:
    """Computes SHA256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(block_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


class ModelManager:
    """
    Manages detection, validation, and directory scanning for translation models.
    """

    def __init__(self, models_root: Optional[Path] = None) -> None:
        self.models_root = models_root or default_paths.models_dir
        self.models_root.mkdir(parents=True, exist_ok=True)

    def get_model_directory(self, model_id: str) -> Path:
        return self.models_root / model_id

    def validate_model_directory(self, dir_path: Path) -> Tuple[bool, str]:
        """
        Validates if a given folder contains a valid CTranslate2 translation model.
        Returns (is_valid, reason_message).
        """
        if not dir_path.is_dir():
            return False, f"المسار ليس مجلداً صحيحاً: {dir_path}"

        # 1. Must contain model.bin
        model_bin = dir_path / "model.bin"
        if not model_bin.is_file() or model_bin.stat().st_size < 1024:
            # Check if this might be a raw HuggingFace PyTorch model
            if (dir_path / "pytorch_model.bin").exists() or (dir_path / "model.safetensors").exists():
                return False, (
                    "هذا المجلد يحتوي على نموذج PyTorch خام وليس نموذج CTranslate2.\n"
                    "يرجى تحويله أولاً باستخدام ct2-transformers-converter أو تنزيل نسخة CTranslate2 الجاهزة."
                )
            return False, "ملف الأوزان الأساسي (model.bin) مفقود أو تالف داخل المجلد."

        # 2. Must contain SentencePiece tokenizer model
        spm_candidates = [
            dir_path / "sentencepiece.bpe.model",
            dir_path / "spm.model",
            dir_path / "flores200_sacrebleu_tokenizer_spm.model",
            dir_path / "source.spm",
        ]
        spm_found = any(p.is_file() and p.stat().st_size > 1000 for p in spm_candidates)
        if not spm_found:
            return False, "ملف معالج الرموز اللغوية SentencePiece (مثل sentencepiece.bpe.model) مفقود داخل المجلد."

        # 3. Must contain vocabulary
        vocab_candidates = [
            dir_path / "shared_vocabulary.txt",
            dir_path / "shared_vocabulary.json",
            dir_path / "source_vocabulary.txt",
            dir_path / "source_vocabulary.json",
        ]
        vocab_found = any(p.is_file() and p.stat().st_size > 100 for p in vocab_candidates)
        if not vocab_found:
            return False, "ملف المفردات (shared_vocabulary.txt أو .json) مفقود داخل المجلد."

        return True, "النموذج مكتمل وصحيح ومتوافق مع CTranslate2."

    def get_model_status(self, model_id: str, custom_path: Optional[Path] = None) -> str:
        """
        Checks status of a catalog model or custom path.
        """
        target_dir = custom_path if custom_path else self.get_model_directory(model_id)
        if not target_dir.exists():
            return ModelStatus.NOT_DOWNLOADED

        catalog_item = CATALOG.get(model_id)
        if not catalog_item:
            valid, _ = self.validate_model_directory(target_dir)
            return ModelStatus.INSTALLED if valid else ModelStatus.INCOMPLETE

        # Check required files
        missing_any = False
        for f in catalog_item.files:
            if f.optional:
                continue
            fp = target_dir / f.filename
            if not fp.exists() or fp.stat().st_size == 0:
                missing_any = True
                break

        if missing_any:
            # Check if any file exists at all
            has_any = any((target_dir / f.filename).exists() for f in catalog_item.files)
            return ModelStatus.INCOMPLETE if has_any else ModelStatus.NOT_DOWNLOADED

        valid, _ = self.validate_model_directory(target_dir)
        return ModelStatus.INSTALLED if valid else ModelStatus.CORRUPTED

    def verify_model_checksums(self, model_id: str, custom_path: Optional[Path] = None) -> Tuple[bool, List[str]]:
        """
        Checks SHA256 checksums for files that have known hashes.
        Returns (all_match, list_of_failed_files).
        """
        catalog_item = CATALOG.get(model_id)
        if not catalog_item:
            return True, []

        target_dir = custom_path if custom_path else self.get_model_directory(model_id)
        failed = []

        for f in catalog_item.files:
            if not f.sha256:
                continue
            fp = target_dir / f.filename
            if not fp.exists():
                failed.append(f"{f.filename} (مفقود)")
                continue
            actual_hash = compute_file_sha256(fp)
            if actual_hash.lower() != f.sha256.lower():
                failed.append(f"{f.filename} (تطابق الشفرة غير صحيح)")

        return (len(failed) == 0), failed

    def scan_models(self) -> List[Dict[str, Any]]:
        """
        Scans models directory and catalog, returning list of available models with statuses.
        """
        result = []
        for model_id, item in CATALOG.items():
            dir_path = self.get_model_directory(model_id)
            status = self.get_model_status(model_id)
            current_size = 0
            if dir_path.exists():
                for p in dir_path.rglob("*"):
                    if p.is_file():
                        current_size += p.stat().st_size

            result.append({
                "id": model_id,
                "name": item.name,
                "description": item.description,
                "architecture": item.architecture,
                "quantization": item.quantization,
                "disk_mb": item.required_disk_mb,
                "ram_mb": item.required_ram_mb,
                "status": status,
                "path": str(dir_path),
                "current_size_bytes": current_size,
                "disclaimer": item.disclaimer,
            })
        return result
