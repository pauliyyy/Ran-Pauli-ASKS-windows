import tempfile
import json
import os
from pathlib import Path
from unittest.mock import patch

import extractor
from mineru_api import MinerUError, MinerUExtraction
from paddleocr_api import PaddleOCRExtraction


def test_single_noncanonical_pdf_is_copied_to_paper_pdf():
    with tempfile.TemporaryDirectory() as directory:
        paper_dir = Path(directory) / "demo"
        paper_dir.mkdir()
        source = paper_dir / "original title.pdf"
        source.write_bytes(b"pdf")
        old_papers_dir = extractor.PAPERS_DIR
        old_extractors = extractor.extract_pymupdf
        extractor.PAPERS_DIR = Path(directory)
        extractor.extract_pymupdf = lambda path, paper_id: "# Demo\n"
        try:
            assert extractor.extract_paper("demo", engine="pymupdf")
            assert (paper_dir / "paper.pdf").read_bytes() == b"pdf"
            assert (paper_dir / "paper.md").exists()
        finally:
            extractor.PAPERS_DIR = old_papers_dir
            extractor.extract_pymupdf = old_extractors


def test_multiple_noncanonical_pdfs_are_rejected():
    with tempfile.TemporaryDirectory() as directory:
        paper_dir = Path(directory) / "demo"
        paper_dir.mkdir()
        (paper_dir / "one.pdf").write_bytes(b"1")
        (paper_dir / "two.pdf").write_bytes(b"2")
        old_papers_dir = extractor.PAPERS_DIR
        extractor.PAPERS_DIR = Path(directory)
        try:
            assert not extractor.extract_paper("demo", engine="pymupdf")
            assert not (paper_dir / "paper.pdf").exists()
        finally:
            extractor.PAPERS_DIR = old_papers_dir


def test_mineru_bundle_keeps_only_referenced_images_and_sidecars():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        paper_dir = root / "paper"
        artifact_root = root / "result"
        (artifact_root / "images").mkdir(parents=True)
        markdown_path = artifact_root / "full.md"
        markdown = "# Demo\n\n![](images/keep.png)\n"
        markdown_path.write_text(markdown, encoding="utf-8")
        keep = artifact_root / "images/keep.png"
        keep.write_bytes(b"keep")
        (artifact_root / "images/unreferenced.png").write_bytes(b"drop")
        layout = artifact_root / "layout.json"
        layout.write_text("{}", encoding="utf-8")
        checkpoint = root / "job.json"
        checkpoint.write_text("{}", encoding="utf-8")
        bundle = MinerUExtraction(
            markdown=markdown,
            markdown_path=markdown_path,
            artifact_root=artifact_root,
            image_paths=(keep,),
            sidecar_paths=(layout,),
            meta={"batch_id": "batch-1"},
            checkpoint_path=checkpoint,
        )
        paper_dir.mkdir()
        meta = extractor._commit_document_bundle(
            paper_dir,
            paper_dir / "paper.md",
            extractor.ExtractionContent(markdown, bundle.meta, bundle),
        )
        assert (paper_dir / "paper.md").read_text(encoding="utf-8") == markdown
        assert (paper_dir / "images/keep.png").read_bytes() == b"keep"
        assert not (paper_dir / "images/unreferenced.png").exists()
        assert (paper_dir / "mineru/layout.json").is_file()
        assert meta["referenced_image_count"] == 1
        assert meta["sidecar_count"] == 1


def test_mineru_bundle_rejects_missing_local_image_without_partial_markdown():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        paper_dir = root / "paper"
        artifact_root = root / "result"
        artifact_root.mkdir()
        paper_dir.mkdir()
        markdown_path = artifact_root / "full.md"
        markdown = "# Demo\n\n![](images/missing.png)\n"
        markdown_path.write_text(markdown, encoding="utf-8")
        bundle = MinerUExtraction(
            markdown=markdown,
            markdown_path=markdown_path,
            artifact_root=artifact_root,
            image_paths=(),
            sidecar_paths=(),
            meta={},
            checkpoint_path=root / "job.json",
        )
        try:
            extractor._commit_document_bundle(
                paper_dir,
                paper_dir / "paper.md",
                extractor.ExtractionContent(markdown, {}, bundle),
            )
        except MinerUError:
            pass
        else:
            raise AssertionError("missing referenced image must fail the document bundle")
        assert not (paper_dir / "paper.md").exists()


def test_mineru_bundle_rejects_non_directory_managed_targets_without_replacing_markdown():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        paper_dir = root / "paper"
        artifact_root = root / "result"
        paper_dir.mkdir()
        artifact_root.mkdir()
        (paper_dir / "paper.md").write_text("# Old\n", encoding="utf-8")
        (paper_dir / "images").write_text("not a directory", encoding="utf-8")
        markdown_path = artifact_root / "full.md"
        markdown_path.write_text("# New\n", encoding="utf-8")
        bundle = MinerUExtraction(
            markdown="# New\n",
            markdown_path=markdown_path,
            artifact_root=artifact_root,
            image_paths=(),
            sidecar_paths=(),
            meta={},
            checkpoint_path=root / "job.json",
        )
        try:
            extractor._commit_document_bundle(
                paper_dir,
                paper_dir / "paper.md",
                extractor.ExtractionContent("# New\n", {}, bundle),
            )
        except MinerUError as exc:
            assert "普通目录" in str(exc)
        else:
            raise AssertionError("managed images target must be a real directory")
        assert (paper_dir / "paper.md").read_text(encoding="utf-8") == "# Old\n"
        assert (paper_dir / "images").is_file()


def test_paddleocr_fallback_is_opt_in_and_atomic_with_honest_metadata():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        paper_dir = root / "demo"
        paper_dir.mkdir()
        (paper_dir / "paper.pdf").write_bytes(b"pdf")
        artifacts = root / "artifacts"
        (artifacts / "images").mkdir(parents=True)
        (artifacts / "images/a.png").write_bytes(b"image")
        bundle = PaddleOCRExtraction("# Paddle\n![a](images/a.png)\n", artifacts, {
            "source": "paddleocr_official_api", "model": "PaddleOCR-VL-1.6",
            "input_sha256": "a" * 64,
        })
        config = {"extraction": {"paddleocr": {"enabled": True}}}
        with patch.object(extractor, "load_config", return_value=config), patch.object(
                extractor, "extract_mineru", return_value=None), patch.object(
                extractor, "extract_paddleocr", return_value=extractor.ExtractionContent(
                    bundle.markdown, bundle.meta, paddleocr_bundle=bundle)) as paddle, patch.object(
                extractor, "extract_blsc_ocr") as blsc, patch.object(extractor, "extract_docling") as docling:
            assert not extractor.extract_paper("demo", papers_dir=root)
            paddle.assert_not_called()
            assert extractor.extract_paper("demo", papers_dir=root, allow_paddleocr=True)
            blsc.assert_not_called()
            docling.assert_not_called()
        meta = extractor.load_parse_meta(paper_dir)
        assert meta["preferred"] == "paddleocr"
        assert "mineru" not in meta["engines"]
        assert meta["engines"]["paddleocr"]["upload_authorization"] == "public_pdf"
        assert meta["engines"]["paddleocr"]["fallback_from"] == "mineru"
        assert (paper_dir / "images/a.png").read_bytes() == b"image"
        assert not (paper_dir / "mineru").exists()


def test_paddleocr_failure_stops_chain_and_private_is_never_uploaded():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        config = {"extraction": {"paddleocr": {"enabled": True}}}
        for location in ("public", "private"):
            paper_dir = root / location / "demo"
            paper_dir.mkdir(parents=True)
            (paper_dir / "paper.pdf").write_bytes(b"pdf")
            with patch.object(extractor, "PROJECT_ROOT", root), patch.object(
                    extractor, "load_config", return_value=config), patch.object(
                    extractor, "extract_mineru", return_value=None), patch.object(
                    extractor, "extract_paddleocr", return_value=None) as paddle, patch.object(
                    extractor, "extract_blsc_ocr") as blsc, patch.object(extractor, "extract_pymupdf") as pymupdf:
                assert not extractor.extract_paper("demo", papers_dir=paper_dir.parent, allow_paddleocr=True)
                assert paddle.call_count == (1 if location == "public" else 0)
                blsc.assert_not_called()
                pymupdf.assert_not_called()
                assert not (paper_dir / "paper.md").exists()
                (paper_dir / "paper.md").write_text("old text", encoding="utf-8")
                extractor.save_parse_meta(paper_dir, {"preferred": "pymupdf"})
                assert not extractor.extract_paper("demo", papers_dir=paper_dir.parent, allow_paddleocr=True)
                assert (paper_dir / "paper.md").read_text(encoding="utf-8") == "old text"


def test_private_external_source_cannot_use_paddleocr_even_in_public_staging():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        paper_dir = root / "public/demo"
        paper_dir.mkdir(parents=True)
        source = root / "private/original.pdf"
        source.parent.mkdir()
        source.write_bytes(b"pdf")
        (paper_dir / "paper.pdf").write_bytes(b"pdf")
        extractor.save_source_yaml(paper_dir, {"external_path": str(source)})
        with patch.object(extractor, "PROJECT_ROOT", root), patch.object(
                extractor, "load_config", return_value={"extraction": {"paddleocr": {"enabled": True}}}), patch.object(
                extractor, "extract_paddleocr") as paddle:
            assert not extractor.extract_paper("demo", engine="paddleocr", papers_dir=paper_dir.parent,
                                               allow_paddleocr=True)
            paddle.assert_not_called()


def test_missing_paddleocr_token_does_not_call_api():
    with patch.dict(os.environ, {"PADDLEOCR_ACCESS_TOKEN": ""}), patch.object(
            extractor, "load_config", return_value={"extraction": {"paddleocr": {"enabled": True}}}), patch.object(
            extractor, "extract_pdf_bundle_with_paddleocr") as remote:
        assert extractor.extract_paddleocr(Path("unused"), "demo") is None
        remote.assert_not_called()


def test_blsc_uses_configured_endpoint_and_visual_model():
    inherited = {
        "LLM_API_BASE": "https://provider.example.test/v1",
        "LLM_API_PATH": "/chat/completions",
        "LLM_API_KEY": "inherited-key",
        "LLM_MODEL": "inherited-model",
    }
    with patch.dict(os.environ, inherited, clear=True):
        inherited_settings = extractor._blsc_api_settings({})
    assert inherited_settings == {
        "endpoint": "https://provider.example.test/v1/chat/completions",
        "key": "inherited-key",
        "model": "inherited-model",
        "fallback_model": "GLM-4.5V",
    }

    environment = {
        "LLM_API_BASE": "https://text.example.test/v1",
        "LLM_API_PATH": "/chat/completions",
        "LLM_API_KEY": "text-key",
        "LLM_MODEL": "text-model",
        "BLSC_OCR_API_BASE": "https://vision.example.test/v1",
        "BLSC_OCR_API_PATH": "/chat/completions",
        "BLSC_OCR_API_KEY": "vision-key",
        "BLSC_OCR_MODEL": "vision-model",
        "BLSC_OCR_FALLBACK_MODEL": "vision-fallback",
    }
    with patch.dict(os.environ, environment, clear=True):
        settings = extractor._blsc_api_settings({})

    assert settings == {
        "endpoint": "https://vision.example.test/v1/chat/completions",
        "key": "vision-key",
        "model": "vision-model",
        "fallback_model": "vision-fallback",
    }

    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"page text"}}]}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return Response()

    with patch.object(extractor.urllib.request, "urlopen", side_effect=fake_urlopen):
        result = extractor._call_blsc_chat(
            settings["endpoint"], settings["key"], settings["model"], [], 37,
            api_path="",
        )

    assert result == "page text"
    assert captured == {
        "url": "https://vision.example.test/v1/chat/completions",
        "payload": {
            "model": "vision-model",
            "messages": [],
            "temperature": 0.1,
            "max_tokens": 4096,
        },
        "timeout": 37,
    }


def test_blsc_retries_an_empty_page_response_without_quality_fallback():
    with tempfile.TemporaryDirectory() as directory:
        paper_dir = Path(directory) / "paper"
        paper_dir.mkdir()
        (paper_dir / "paper.pdf").write_bytes(b"pdf")
        settings = {
            "endpoint": "https://vision.example.test/v1/chat/completions",
            "key": "vision-key",
            "model": "vision-model",
            "fallback_model": "vision-model",
        }
        with (
            patch.object(extractor, "_blsc_ocr_config", return_value={"page_attempts": 3}),
            patch.object(extractor, "_blsc_api_settings", return_value=settings),
            patch.object(extractor, "_render_pdf_pages", return_value=[b"png"]),
            patch.object(
                extractor,
                "_call_blsc_chat",
                side_effect=[RuntimeError("BLSC OCR 返回空内容"), "page text"],
            ) as call,
            patch.object(extractor.time, "sleep") as sleep,
        ):
            result = extractor.extract_blsc_ocr(paper_dir, "paper")

    assert result == "<!-- Page 1 -->\n\npage text"
    assert call.call_count == 2
    sleep.assert_called_once_with(1)


def test_root_config_is_used_and_project_config_has_priority():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        project_config = root / ".project" / "config.yaml"
        root_config = root / "config.yaml"
        root_config.write_text(
            "extraction:\n  mineru:\n    model_version: pipeline\n",
            encoding="utf-8",
        )
        with (
            patch.object(extractor, "CONFIG_PATH", project_config),
            patch.object(extractor, "ROOT_CONFIG_PATH", root_config),
        ):
            assert extractor.load_config()["extraction"]["mineru"]["model_version"] == "pipeline"
            project_config.parent.mkdir(parents=True)
            project_config.write_text("source: project\n", encoding="utf-8")
            assert extractor.load_config() == {"source": "project"}


def test_blsc_environment_override_can_disable_visual_fallback():
    with patch.dict(os.environ, {"BLSC_OCR_ENABLED": "0"}, clear=False):
        assert extractor._blsc_ocr_config()["enabled"] is False


def test_successful_mineru_extraction_does_not_call_lower_priority_engines():
    with tempfile.TemporaryDirectory() as directory:
        papers_dir = Path(directory)
        paper_dir = papers_dir / "demo"
        paper_dir.mkdir()
        (paper_dir / "paper.pdf").write_bytes(b"pdf")
        output = extractor.ExtractionContent("# MinerU\n", {"source": "api"})
        with (
            patch.object(extractor, "extract_mineru", return_value=output),
            patch.object(extractor, "extract_blsc_ocr") as blsc,
            patch.object(extractor, "extract_docling") as docling,
            patch.object(extractor, "extract_pymupdf") as pymupdf,
            patch.object(
                extractor,
                "load_config",
                return_value={"extraction": {"mineru": {"keep_archive": True}}},
            ),
        ):
            assert extractor.extract_paper("demo", papers_dir=papers_dir)

        assert (paper_dir / "paper.md").read_text(encoding="utf-8") == "# MinerU\n"
        assert extractor.load_parse_meta(paper_dir)["preferred"] == "mineru"
        blsc.assert_not_called()
        docling.assert_not_called()
        pymupdf.assert_not_called()


def test_failed_mineru_and_visual_fallback_do_not_silently_use_local_engines():
    with tempfile.TemporaryDirectory() as directory:
        papers_dir = Path(directory)
        paper_dir = papers_dir / "demo"
        paper_dir.mkdir()
        (paper_dir / "paper.pdf").write_bytes(b"pdf")
        with (
            patch.object(extractor, "extract_mineru", return_value=None),
            patch.object(extractor, "extract_blsc_ocr", return_value=None),
            patch.object(extractor, "extract_docling") as docling,
            patch.object(extractor, "extract_pymupdf") as pymupdf,
        ):
            assert not extractor.extract_paper("demo", papers_dir=papers_dir)

        assert not (paper_dir / "paper.md").exists()
        docling.assert_not_called()
        pymupdf.assert_not_called()


def test_blsc_upstream_base_url_keyword_and_linux_custom_endpoint():
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def read(self):
            return b'{"choices":[{"message":{"content":"verified"}}]}'
    cases = [
        ("https://example.invalid", "/v1/chat/completions", "https://example.invalid/v1/chat/completions"),
        ("https://example.invalid/v1", "/v1/chat/completions", "https://example.invalid/v1/chat/completions"),
        ("https://example.invalid/openai", "/v1/chat/completions", "https://example.invalid/openai/v1/chat/completions"),
        ("https://example.invalid/custom/ocr", "", "https://example.invalid/custom/ocr"),
    ]
    for base, api_path, expected in cases:
        with patch.object(extractor.urllib.request, "urlopen", return_value=Response()) as transport:
            kwargs = {"api_path": api_path} if not api_path else {}
            assert extractor._call_blsc_chat(base_url=base, key="fixture", model="visual", messages=[], timeout_sec=10, **kwargs) == "verified"
            assert transport.call_args.args[0].full_url == expected


if __name__ == "__main__":
    test_blsc_upstream_base_url_keyword_and_linux_custom_endpoint()
    test_single_noncanonical_pdf_is_copied_to_paper_pdf()
    test_multiple_noncanonical_pdfs_are_rejected()
    test_mineru_bundle_keeps_only_referenced_images_and_sidecars()
    test_mineru_bundle_rejects_missing_local_image_without_partial_markdown()
    test_mineru_bundle_rejects_non_directory_managed_targets_without_replacing_markdown()
    test_paddleocr_fallback_is_opt_in_and_atomic_with_honest_metadata()
    test_paddleocr_failure_stops_chain_and_private_is_never_uploaded()
    test_missing_paddleocr_token_does_not_call_api()
    test_private_external_source_cannot_use_paddleocr_even_in_public_staging()
    test_blsc_uses_configured_endpoint_and_visual_model()
    test_blsc_retries_an_empty_page_response_without_quality_fallback()
    test_root_config_is_used_and_project_config_has_priority()
    test_blsc_environment_override_can_disable_visual_fallback()
    test_successful_mineru_extraction_does_not_call_lower_priority_engines()
    test_failed_mineru_and_visual_fallback_do_not_silently_use_local_engines()
    print("extractor regression: PASS")
