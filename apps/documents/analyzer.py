"""
Singleton wrapper around the PPStructureV3 DocumentAnalyzer.

The analyzer is initialised once at Django startup (via DocumentsConfig.ready)
and reused for every processing request. Thread-safety is ensured by a module-level
lock so that concurrent startup calls don't produce two instances.
"""

from __future__ import annotations

import io
import logging
import threading
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_analyzer_instance: "DocumentAnalyzer | None" = None
_init_error: Exception | None = None


class DocumentAnalyzer:
    """
    Wraps PPStructureV3 to analyse documents and produce:
    - A layout-annotated PDF
    - A Markdown transcription
    """

    def __init__(self, output_dir: str | Path = "") -> None:
        if not output_dir:
            output_dir = settings.DOCUMENTS_OUTPUT_DIR

        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Loading PPStructureV3 model…")
        from paddleocr import PPStructureV3  # type: ignore[import]

        self.pipeline = PPStructureV3()
        logger.info("PPStructureV3 loaded successfully.")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def predict(self, input_file: str | Path) -> list:
        results = self.pipeline.predict(input=str(input_file))
        return list(results)

    def generate_layout_pdf(self, results: list, output_file: str | Path) -> None:
        import fitz  # type: ignore[import]

        pdf_doc = fitz.open()
        for res in results:
            layout = res.get("layout_det_res")
            if layout is None:
                continue
            img = layout.img["res"].convert("RGB")
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=90, optimize=True)
            page = pdf_doc.new_page(width=img.width, height=img.height)
            page.insert_image(page.rect, stream=buffer.getvalue())
            buffer.close()
            img.close()

        pdf_doc.save(str(output_file), garbage=4, deflate=True)
        pdf_doc.close()

    def generate_markdown(self, results: list, output_file: str | Path) -> None:
        markdown: list[str] = []
        images: dict = {}
        for res in results:
            md_info = res.markdown
            text = md_info.get("markdown_texts", "")
            if text:
                markdown.append(text)
            imgs = md_info.get("markdown_images", {})
            if imgs:
                images.update(imgs)

        with open(str(output_file), "w", encoding="utf-8") as f:
            f.write("\n\n---\n\n".join(markdown))

        self._save_images(images, Path(output_file).parent)

    def _save_images(self, images: dict, output_dir: Path) -> None:
        for rel_path, image in images.items():
            img_path = output_dir / rel_path
            img_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(img_path)

    # ── Public API ────────────────────────────────────────────────────────────

    def process_document(self, input_file: str | Path, output_dir: str | Path) -> dict:
        """
        Analyse *input_file* and write outputs to *output_dir*.

        Returns:
            {
                "layout_pdf": Path,
                "markdown": Path,
                "pages": int,
            }
        """
        input_path = Path(input_file)
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        stem = input_path.stem
        results = self.predict(input_path)

        layout_pdf = out_dir / f"{stem}_layout.pdf"
        markdown_file = out_dir / f"{stem}.md"

        self.generate_layout_pdf(results, layout_pdf)
        self.generate_markdown(results, markdown_file)

        return {
            "layout_pdf": layout_pdf,
            "markdown": markdown_file,
            "pages": len(results),
        }


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

def get_analyzer() -> DocumentAnalyzer:
    """
    Return the module-level singleton, initialising it on first call.
    Raises AnalyzerUnavailableError if the model could not be loaded.
    """
    global _analyzer_instance, _init_error

    if _analyzer_instance is not None:
        return _analyzer_instance

    with _lock:
        # Double-checked locking
        if _analyzer_instance is not None:
            return _analyzer_instance

        if _init_error is not None:
            from core.exceptions import AnalyzerUnavailableError
            raise AnalyzerUnavailableError(
                f"Document analyzer failed to initialise: {_init_error}"
            )

        try:
            _analyzer_instance = DocumentAnalyzer()
        except Exception as exc:
            _init_error = exc
            logger.exception("Fatal: DocumentAnalyzer could not be loaded.")
            from core.exceptions import AnalyzerUnavailableError
            raise AnalyzerUnavailableError(
                f"Document analyzer failed to initialise: {exc}"
            ) from exc

    return _analyzer_instance
