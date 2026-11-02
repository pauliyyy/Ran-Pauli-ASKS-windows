#!/usr/bin/env python3
"""Offline shared Office extraction and ingestion-preview regressions."""
from __future__ import annotations

import ast
import hashlib
import json
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import document_text


def _executable(path: Path) -> Path:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_docx_structured_text_extraction(tmp: Path) -> None:
    source = tmp / "sample.docx"
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="{document_text.WORD_NS}" xmlns:r="{document_text.OFFICE_REL_NS}"><w:body>
  <w:p><w:r><w:t>Title</w:t><w:footnoteReference w:id="1"/><w:endnoteReference w:id="1"/></w:r></w:p>
  <w:tbl><w:tr>
    <w:tc><w:p><w:r><w:t>A1</w:t></w:r></w:p></w:tc>
    <w:tc><w:p><w:r><w:t>B1</w:t></w:r></w:p></w:tc>
  </w:tr></w:tbl>
  <w:sdt><w:sdtContent><w:p><w:r><w:t>Nested</w:t></w:r></w:p></w:sdtContent></w:sdt>
  <w:p><w:r><w:t>Line</w:t><w:tab/><w:t>two</w:t><w:br/><w:t>tail</w:t></w:r></w:p>
  <w:sectPr><w:headerReference r:id="rHeader"/><w:footerReference r:id="rFooter"/></w:sectPr>
</w:body></w:document>"""
    header = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:hdr xmlns:w="{document_text.WORD_NS}">
  <w:p><w:r><w:t>Header</w:t></w:r></w:p>
</w:hdr>"""
    footer = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:ftr xmlns:w="{document_text.WORD_NS}">
  <w:p><w:r><w:t>Footer</w:t></w:r></w:p>
</w:ftr>"""
    footnotes = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:footnotes xmlns:w="{document_text.WORD_NS}">
  <w:footnote w:id="1"><w:p><w:r><w:t>Footnote</w:t></w:r></w:p></w:footnote>
  <w:footnote w:id="2"><w:p><w:r><w:t>Orphan footnote</w:t></w:r></w:p></w:footnote>
</w:footnotes>"""
    endnotes = f"""<?xml version="1.0" encoding="UTF-8"?>
<w:endnotes xmlns:w="{document_text.WORD_NS}">
  <w:endnote w:id="1"><w:p><w:r><w:t>Endnote</w:t></w:r></w:p></w:endnote>
  <w:endnote w:id="2"><w:p><w:r><w:t>Orphan endnote</w:t></w:r></w:p></w:endnote>
</w:endnotes>"""
    relationships = f"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="{document_text.PACKAGE_REL_NS}">
  <Relationship Id="rHeader" Type="{document_text.OFFICE_REL_NS}/header" Target="header1.xml"/>
  <Relationship Id="rFooter" Type="{document_text.OFFICE_REL_NS}/footer" Target="footer1.xml"/>
  <Relationship Id="rFootnotes" Type="{document_text.OFFICE_REL_NS}/footnotes" Target="footnotes.xml"/>
  <Relationship Id="rEndnotes" Type="{document_text.OFFICE_REL_NS}/endnotes" Target="endnotes.xml"/>
</Relationships>"""
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("word/document.xml", xml)
        archive.writestr("word/_rels/document.xml.rels", relationships)
        archive.writestr("word/header1.xml", header)
        archive.writestr("word/footer1.xml", footer)
        archive.writestr("word/header-orphan.xml", header.replace("Header", "Orphan header"))
        archive.writestr("word/footer-orphan.xml", footer.replace("Footer", "Orphan footer"))
        archive.writestr("word/footnotes.xml", footnotes)
        archive.writestr("word/endnotes.xml", endnotes)
    assert document_text.extract_word_text(source) == (
        "Title\nA1\tB1\nNested\nLine\ttwo\ntail\n\nHeader\n\nFooter\n\n"
        "Footnote\n\nEndnote\n"
    )
    assert document_text.extract_word_text(source, max_chars=5) == "Title"

    strict_source = tmp / "strict.docx"
    strict_parts = {
        "word/document.xml": xml,
        "word/_rels/document.xml.rels": relationships,
        "word/header1.xml": header,
        "word/footer1.xml": footer,
        "word/footnotes.xml": footnotes,
        "word/endnotes.xml": endnotes,
    }
    with zipfile.ZipFile(strict_source, "w") as archive:
        for name, content in strict_parts.items():
            content = content.replace(
                document_text.WORD_NS, document_text.STRICT_WORD_NS
            ).replace(
                document_text.OFFICE_REL_NS,
                document_text.STRICT_OFFICE_REL_NS,
            )
            archive.writestr(name, content)
    assert document_text.extract_word_text(strict_source) == (
        "Title\nA1\tB1\nNested\nLine\ttwo\ntail\n\nHeader\n\nFooter\n\n"
        "Footnote\n\nEndnote\n"
    )


def test_docx_alternate_content_selects_supported_choice_or_fallback(tmp: Path) -> None:
    mc = document_text.MC_NS
    xml = f"""<w:document xmlns:w="{document_text.WORD_NS}" xmlns:r="{document_text.OFFICE_REL_NS}" xmlns:mc="{mc}" xmlns:unknown="urn:unsupported-asks-test"><w:body>
<w:p><w:r><w:t>Body</w:t><mc:AlternateContent><mc:Choice Requires="unknown"><w:t>HIDDEN_RUN</w:t></mc:Choice><mc:Fallback><w:t>VisibleRun</w:t></mc:Fallback></mc:AlternateContent></w:r></w:p>
<mc:AlternateContent><mc:Choice Requires="unknown"><w:p><w:r><w:t>HIDDEN_BODY</w:t></w:r></w:p></mc:Choice><mc:Fallback><w:p><w:r><w:t>VisibleBody</w:t></w:r></w:p></mc:Fallback></mc:AlternateContent>
<mc:AlternateContent><mc:Choice Requires="unknown"><w:p><w:r><w:t>HIDDEN_FIRST_CHOICE</w:t></w:r></w:p></mc:Choice><mc:Choice Requires="w"><w:p><w:r><w:t>VisibleSupportedChoice</w:t></w:r></w:p></mc:Choice><mc:Fallback><w:p><w:r><w:t>HIDDEN_SUPPORTED_FALLBACK</w:t></w:r></w:p></mc:Fallback></mc:AlternateContent>
<w:sectPr><mc:AlternateContent><mc:Choice Requires="unknown"><w:headerReference r:id="hidden"/></mc:Choice><mc:Fallback><w:headerReference r:id="visible"/></mc:Fallback></mc:AlternateContent></w:sectPr>
</w:body></w:document>"""
    header = f'<w:hdr xmlns:w="{document_text.WORD_NS}" xmlns:mc="{mc}" xmlns:unknown="urn:unsupported-asks-test"><mc:AlternateContent><mc:Choice Requires="unknown"><w:p><w:r><w:t>HIDDEN_HEADER_BRANCH</w:t></w:r></w:p></mc:Choice><mc:Fallback><w:p><w:r><w:t>VisibleHeader</w:t></w:r></w:p></mc:Fallback></mc:AlternateContent></w:hdr>'
    rels = f'<Relationships xmlns="{document_text.PACKAGE_REL_NS}"><Relationship Id="visible" Type="{document_text.OFFICE_REL_NS}/header" Target="header-visible.xml"/><Relationship Id="hidden" Type="{document_text.OFFICE_REL_NS}/header" Target="header-hidden.xml"/></Relationships>'
    parts = {"word/document.xml": xml, "word/_rels/document.xml.rels": rels,
             "word/header-visible.xml": header,
             "word/header-hidden.xml": f'<w:hdr xmlns:w="{document_text.WORD_NS}"><w:p><w:r><w:t>HIDDEN_REFERENCE</w:t></w:r></w:p></w:hdr>'}
    for strict in (False, True):
        source = tmp / ("mc-strict.docx" if strict else "mc.docx")
        with zipfile.ZipFile(source, "w") as archive:
            for name, content in parts.items():
                if strict:
                    content = content.replace(document_text.WORD_NS, document_text.STRICT_WORD_NS).replace(document_text.OFFICE_REL_NS, document_text.STRICT_OFFICE_REL_NS)
                archive.writestr(name, content)
        before = source.read_bytes()
        assert document_text.extract_word_text(source) == "BodyVisibleRun\nVisibleBody\nVisibleSupportedChoice\n\nVisibleHeader\n"
        assert source.read_bytes() == before
        unsupported = tmp / ("mc-no-fallback-strict.docx" if strict else "mc-no-fallback.docx")
        with zipfile.ZipFile(unsupported, "w") as archive:
            for name, content in parts.items():
                if name == "word/document.xml":
                    content = content.replace('<mc:Fallback><w:t>VisibleRun</w:t></mc:Fallback>', '')
                if strict:
                    content = content.replace(document_text.WORD_NS, document_text.STRICT_WORD_NS).replace(document_text.OFFICE_REL_NS, document_text.STRICT_OFFICE_REL_NS)
                archive.writestr(name, content)
        assert document_text.extract_word_text(unsupported) == ""


def test_legacy_doc_uses_soffice_without_persisting_conversion(tmp: Path) -> None:
    source = tmp / "legacy.doc"
    source.write_bytes(b"legacy")
    soffice = _executable(tmp / "soffice")
    original_executable = document_text.platform_compat.find_executable
    original_soffice = document_text.platform_compat.find_soffice
    original_environment = document_text.platform_compat.soffice_environment
    original_run = document_text.subprocess.run
    output_dirs: list[Path] = []

    def run(command, **kwargs):
        assert kwargs["env"] == {"LANG": "C.UTF-8"}
        output_dir = Path(command[command.index("--outdir") + 1])
        output_dirs.append(output_dir)
        assert command[command.index("--convert-to") + 1] == "docx"
        assert output_dir.parent != source.parent
        parts = {
            "word/document.xml": f'<w:document xmlns:w="{document_text.WORD_NS}" xmlns:r="{document_text.OFFICE_REL_NS}"><w:body><w:p><w:r><w:t>portable text</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:sectPr><w:headerReference r:id="h"/><w:footerReference r:id="f"/></w:sectPr></w:body></w:document>',
            "word/_rels/document.xml.rels": f'<Relationships xmlns="{document_text.PACKAGE_REL_NS}"><Relationship Id="h" Type="{document_text.OFFICE_REL_NS}/header" Target="header.xml"/><Relationship Id="f" Type="{document_text.OFFICE_REL_NS}/footer" Target="footer.xml"/></Relationships>',
            "word/header.xml": f'<w:hdr xmlns:w="{document_text.WORD_NS}"><w:p><w:r><w:t>Header</w:t></w:r></w:p></w:hdr>',
            "word/footer.xml": f'<w:ftr xmlns:w="{document_text.WORD_NS}"><w:p><w:r><w:t>Footer</w:t></w:r></w:p></w:ftr>',
        }
        with zipfile.ZipFile(output_dir / "legacy.docx", "w") as archive:
            for name, content in parts.items():
                archive.writestr(name, content)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    try:
        document_text.platform_compat.find_executable = lambda *_names: None
        document_text.platform_compat.find_soffice = lambda: soffice
        document_text.platform_compat.soffice_environment = lambda _path: {
            "LANG": "C.UTF-8"
        }
        document_text.subprocess.run = run
        assert document_text.extract_word_text(source) == "portable text\nCell\n\nHeader\n\nFooter\n"
        assert document_text.extract_word_text(source, max_chars=8) == "portable"
        assert source.read_bytes() == b"legacy"
    finally:
        document_text.platform_compat.find_executable = original_executable
        document_text.platform_compat.find_soffice = original_soffice
        document_text.platform_compat.soffice_environment = original_environment
        document_text.subprocess.run = original_run
    assert output_dirs and all(not path.exists() for path in output_dirs)


def _docx(path: Path, body: str, *, namespace: str = document_text.WORD_NS,
          parts: dict[str, str] | None = None) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", f'<w:document xmlns:w="{namespace}"><w:body>{body}</w:body></w:document>')
        for name, content in (parts or {}).items():
            archive.writestr(name, content)
    return path


def test_invalid_inputs_and_source_preservation(tmp: Path) -> None:
    assert document_text.extract_word_text(tmp / "missing.docx") == ""
    broken = tmp / "broken.docx"
    broken.write_bytes(b"not a ZIP archive")
    assert document_text.extract_word_text(broken) == ""
    with zipfile.ZipFile(broken, "w") as archive:
        archive.writestr("not-the-document.xml", "missing main part")
    assert document_text.extract_word_text(broken) == ""
    for index, content in enumerate(("<broken", '<document xmlns="urn:unknown"/>',
                                   f'<w:document xmlns:w="{document_text.WORD_NS}"/>')):
        path = tmp / f"bad-{index}.docx"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", content)
        original = path.read_bytes()
        assert document_text.extract_word_text(path) == ""
        assert path.read_bytes() == original
    assert document_text.extract_word_text(tmp / "unsupported.pdf") == ""


def test_relationships_and_inline_control_characters(tmp: Path) -> None:
    w, r, pr = document_text.WORD_NS, document_text.OFFICE_REL_NS, document_text.PACKAGE_REL_NS
    xml = f'<w:document xmlns:w="{w}" xmlns:r="{r}"><w:body><w:p><w:r><w:t>可见</w:t><w:noBreakHyphen/><w:t>A</w:t><w:softHyphen/><w:t>B</w:t><w:cr/><w:t>尾行</w:t></w:r></w:p><w:sectPr><w:headerReference r:id="external"/><w:headerReference r:id="outside"/><w:footerReference r:id="absolute"/></w:sectPr></w:body></w:document>'
    relationships = f'<Relationships xmlns="{pr}"><Relationship Id="external" Type="{r}/header" Target="https://example.invalid/private" TargetMode="External"/><Relationship Id="outside" Type="{r}/header" Target="../../escape.xml"/><Relationship Id="absolute" Type="{r}/footer" Target="/word/orphan.xml"/></Relationships>'
    path = tmp / "relations.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)
        archive.writestr("word/_rels/document.xml.rels", relationships)
        archive.writestr("word/orphan.xml", f'<w:hdr xmlns:w="{w}"><w:p><w:r><w:t>HIDDEN</w:t></w:r></w:p></w:hdr>')
    original = path.read_bytes()
    assert document_text.extract_word_text(path) == "可见-A-B\n尾行\n"
    assert path.read_bytes() == original
    # A damaged relationship part does not discard the still-readable main body.
    path = _docx(tmp / "bad-rels.docx", '<w:p><w:r><w:t>Body</w:t></w:r></w:p>',
                 parts={"word/_rels/document.xml.rels": "<broken"})
    assert document_text.extract_word_text(path) == "Body\n"


def test_scoped_alternate_content_prefixes(tmp: Path) -> None:
    w, mc = document_text.WORD_NS, document_text.MC_NS
    body = f'<mc:AlternateContent xmlns:mc="{mc}" xmlns:alias="{w}"><mc:Choice Requires="alias"><w:p><w:r><w:t>Supported</w:t></w:r></w:p><mc:AlternateContent xmlns:alias="urn:unknown"><mc:Choice Requires="alias"><w:p><w:r><w:t>HIDDEN</w:t></w:r></w:p></mc:Choice><mc:Fallback><w:p><w:r><w:t>ScopedFallback</w:t></w:r></w:p></mc:Fallback></mc:AlternateContent></mc:Choice><mc:Fallback><w:p><w:r><w:t>HIDDEN_FALLBACK</w:t></w:r></w:p></mc:Fallback></mc:AlternateContent>'
    path = _docx(tmp / "scoped.docx", body)
    assert document_text.extract_word_text(path) == "Supported\nScopedFallback\n"


def test_converter_result_failure_timeout_and_precedence(tmp: Path) -> None:
    with patch.object(document_text.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="result")) as run:
        assert document_text._run_text_command(["converter", "source"]) == "result"
        assert run.call_args.kwargs["encoding"] == "utf-8"
        assert run.call_args.kwargs["errors"] == "replace"
        assert run.call_args.kwargs["timeout"] == 120
    for outcome in (SimpleNamespace(returncode=1, stdout="discard"),
                    FileNotFoundError("missing converter"), subprocess.TimeoutExpired("converter", 120)):
        kwargs = {"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome}
        with patch.object(document_text.subprocess, "run", **kwargs):
            assert document_text._run_text_command(["converter", "source"]) == ""
    source = tmp / "legacy.doc"
    source.write_bytes(b"unchanged legacy source")
    original = source.read_bytes()
    tools = {name: Path("/diagnostic") / name for name in ("textutil", "antiword", "catdoc")}
    def find(name):
        return tools.get(name)
    with patch.object(document_text.platform_compat, "find_executable", side_effect=find), \
         patch.object(document_text.platform_compat, "find_soffice", return_value=Path("/diagnostic/soffice")) as office, \
         patch.object(document_text, "_run_text_command", return_value="mac text") as command, \
         patch.object(document_text, "_extract_doc_with_soffice", return_value="office text") as convert:
        assert document_text.extract_word_text(source) == "mac text"
        assert command.call_args.args[0][1:4] == ["-convert", "txt", "-stdout"]
        office.assert_not_called(); convert.assert_not_called()
        command.reset_mock(); command.return_value = ""
        assert document_text.extract_word_text(source) == "office text"
        convert.assert_called_once_with(source, Path("/diagnostic/soffice"), timeout=180)
        command.reset_mock(); convert.return_value = ""
        command.side_effect = lambda argv, **_kwargs: "antiword text" if argv[0].endswith("antiword") else ""
        assert document_text.extract_word_text(source) == "antiword text"
        assert command.call_args.args[0] == [str(tools["antiword"]), str(source)]
        command.side_effect = lambda argv, **_kwargs: "catdoc text" if argv[0].endswith("catdoc") else ""
        assert document_text.extract_word_text(source) == "catdoc text"
    with patch.object(document_text.platform_compat, "find_executable", return_value=None), \
         patch.object(document_text.platform_compat, "find_soffice", return_value=None):
        assert document_text.extract_word_text(source) == ""
    for outcome in (SimpleNamespace(returncode=1), SimpleNamespace(returncode=0),
                    FileNotFoundError("missing"), subprocess.TimeoutExpired("soffice",180)):
        kwargs = {"side_effect": outcome} if isinstance(outcome, Exception) else {"return_value": outcome}
        with patch.object(document_text.subprocess, "run", **kwargs), \
             patch.object(document_text.platform_compat, "soffice_environment", return_value={}):
            assert document_text._extract_doc_with_soffice(source, Path("/diagnostic/soffice")) == ""
    assert source.read_bytes() == original


def test_ingest_entrypoints_share_native_word_text(tmp: Path) -> None:
    import ingest_document
    import ingest_inbox
    path = _docx(tmp / "会议 速记.DOCX", '<w:p><w:r><w:t>会议速记：甲方发言</w:t></w:r></w:p>')
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    with patch.object(document_text.subprocess, "run", side_effect=AssertionError("DOCX must not spawn host tools")):
        expected = document_text.extract_word_text(path)
        assert ingest_document.extract_doc_text(path) == expected
        for limit in (8000, 5, 0, -1):
            assert ingest_inbox.read_document_preview(path, max_chars=limit) == expected[:limit]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    with patch.object(document_text, "extract_word_text", return_value="legacy shared text") as shared:
        legacy = tmp / "legacy.doc"
        assert ingest_document.extract_doc_text(legacy) == "legacy shared text"
        assert ingest_inbox.read_document_preview(legacy, max_chars=6) == "legacy"
        assert shared.call_count == 2
        assert shared.call_args_list[0].args == (legacy,)
        assert shared.call_args_list[0].kwargs == {"timeout": 120}
        assert shared.call_args_list[1].args == (legacy,)
        assert shared.call_args_list[1].kwargs == {"timeout": 30}
    for failure in (OSError("unreadable"), UnicodeError("undecodable"), subprocess.TimeoutExpired("converter", 30)):
        with patch.object(document_text, "extract_word_text", side_effect=failure):
            assert ingest_inbox.read_document_preview(path) == ""
    with patch.object(document_text, "extract_word_text", side_effect=OSError("unreadable")):
        try:
            ingest_document.extract_doc_text(path)
        except OSError:
            pass
        else:
            raise AssertionError("formal extraction must preserve caller exception propagation")


def test_total_converter_deadline_and_short_failure_fallback(tmp: Path) -> None:
    source = tmp / "deadline.doc"
    source.write_bytes(b"legacy source remains unchanged")
    original = source.read_bytes()
    for budget, expected_caps in ((30, [30, 28, 25, 20]),
                                  (500, [120, 180, 120, 120])):
        clock = [100.0]
        invocations = []
        def run(command, **kwargs):
            index = len(invocations)
            name = Path(command[0]).name
            assert kwargs["timeout"] == expected_caps[index]
            invocations.append(name)
            clock[0] += (2, 3, 5, 1)[index]
            return SimpleNamespace(returncode=0 if name == "catdoc" else 1,
                                   stdout="bounded fallback text" if name == "catdoc" else "", stderr="")
        with patch.object(document_text.time, "monotonic", side_effect=lambda: clock[0]), \
             patch.object(document_text.platform_compat, "find_executable", side_effect=lambda name: Path("/diagnostic") / name), \
             patch.object(document_text.platform_compat, "find_soffice", return_value=Path("/diagnostic/soffice")), \
             patch.object(document_text.platform_compat, "soffice_environment", return_value={}), \
             patch.object(document_text.subprocess, "run", side_effect=run):
            assert document_text.extract_word_text(source, timeout=budget) == "bounded fallback text"
            assert invocations == ["textutil", "soffice", "antiword", "catdoc"]
    assert source.read_bytes() == original


def test_exhausted_deadline_starts_no_later_converter(tmp: Path) -> None:
    source = tmp / "exhausted.doc"
    source.write_bytes(b"legacy")
    clock = [100.0]
    def run(command, **kwargs):
        assert Path(command[0]).name == "textutil"
        assert kwargs["timeout"] == 30
        clock[0] += kwargs["timeout"]
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])
    with patch.object(document_text.time, "monotonic", side_effect=lambda: clock[0]), \
         patch.object(document_text.platform_compat, "find_executable", return_value=Path("/diagnostic/textutil")) as find, \
         patch.object(document_text.platform_compat, "find_soffice") as office, \
         patch.object(document_text.subprocess, "run", side_effect=run) as execute:
        assert document_text.extract_word_text(source, timeout=30) == ""
        execute.assert_called_once()
        find.assert_called_once_with("textutil")
        office.assert_not_called()
    for budget in (0, -1):
        with patch.object(document_text.platform_compat, "find_executable") as find, \
             patch.object(document_text.platform_compat, "find_soffice") as office, \
             patch.object(document_text.subprocess, "run") as execute:
            assert document_text.extract_word_text(source, timeout=budget) == ""
            find.assert_not_called(); office.assert_not_called(); execute.assert_not_called()


def test_ooxml_parsing_does_not_start_a_converter_deadline(tmp: Path) -> None:
    source = _docx(tmp / "native.docx", '<w:p><w:r><w:t>Native text</w:t></w:r></w:p>')
    with patch.object(document_text.time, "monotonic", side_effect=AssertionError("DOCX does not need a conversion deadline")), \
         patch.object(document_text.subprocess, "run", side_effect=AssertionError("DOCX must remain native")):
        assert document_text.extract_word_text(source, timeout=0) == "Native text\n"
        assert document_text.extract_word_text(source, max_chars=0, timeout=0) == ""
        assert document_text.extract_word_text(source, max_chars=-1, timeout=0) == ""


def test_pptx_preview_uses_shared_native_slide_order(tmp: Path) -> None:
    from pptx import Presentation
    from pptx.util import Inches
    import ingest_document
    import ingest_inbox
    import pptx_document
    deck = Presentation()
    markers = ("STORED_FIRST_PRESENTED_SECOND", "STORED_SECOND_PRESENTED_FIRST")
    for marker in markers:
        slide = deck.slides.add_slide(deck.slide_layouts[6])
        slide.shapes.add_textbox(Inches(1), Inches(1), Inches(7), Inches(1)).text = marker
    slide_ids = deck.slides._sldIdLst
    for element in list(slide_ids):
        slide_ids.remove(element); slide_ids.insert(0, element)
    source = tmp / "two slides.PPTX"
    deck.save(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    expected, manifest = pptx_document.extract(source)
    assert [page["part"] for page in manifest["pages"]] == ["ppt/slides/slide2.xml", "ppt/slides/slide1.xml"]
    assert expected.index(markers[1]) < expected.index(markers[0])
    with patch.object(ingest_inbox.subprocess, "run", side_effect=AssertionError("PPTX preview must not invoke pandoc or a remote adapter")), \
         patch.object(pptx_document, "extract", wraps=pptx_document.extract) as shared:
        assert ingest_inbox.read_document_preview(source) == expected
        shared.assert_called_once_with(source)
        assert ingest_document.extract_doc_text(source) == expected
        for limit in (8000, 10, 0, -1):
            assert ingest_inbox.read_document_preview(source, max_chars=limit) == expected[:limit]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert ingest_inbox.read_document_preview(tmp / "missing.pptx") == ""
    broken = tmp / "not-a-zip.pptx"; broken.write_bytes(b"invalid archive")
    assert ingest_inbox.read_document_preview(broken) == ""
    for index, contents in enumerate(({"unrelated.xml": "missing main part"},
                                      {"ppt/presentation.xml": "<broken"},
                                      {"ppt/presentation.xml": f'<p:presentation xmlns:p="{pptx_document.NS["p"]}"/>'})):
        broken = tmp / f"broken-{index}.pptx"
        with zipfile.ZipFile(broken, "w") as archive:
            for name, value in contents.items(): archive.writestr(name, value)
        assert ingest_inbox.read_document_preview(broken) == ""
    with patch.object(pptx_document, "extract", side_effect=AssertionError("unexpected implementation error")):
        try:
            ingest_inbox.read_document_preview(source)
        except AssertionError:
            pass
        else:
            raise AssertionError("Unexpected implementation defects must not be hidden as an empty preview")


def main() -> None:
    target = Path(document_text.__file__).resolve()
    defined = {node.name for node in ast.parse(target.read_text()).body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    called: set[str] = set()
    def profile(frame, event, _arg):
        if event == "call" and Path(frame.f_code.co_filename).resolve() == target:
            called.add(frame.f_code.co_name)
    tests = sorted((name, value) for name, value in globals().items() if name.startswith("test_") and callable(value))
    sys.setprofile(profile)
    try:
        with tempfile.TemporaryDirectory(prefix="asks-word-test-") as folder:
            for index, (name, test) in enumerate(tests):
                workspace = Path(folder) / str(index); workspace.mkdir()
                test(workspace)
                print(f"PASS {name}")
    finally:
        sys.setprofile(None)
    missing = sorted(defined - called)
    assert not missing, f"Unexecuted Word extraction definitions: {missing}"
    print(json.dumps({"schema": "asks-word-extraction-regression-v1", "status": "pass", "test_groups": len(tests),
                      "module_top_level_definitions": len(defined), "executed_top_level_definitions": sorted(defined & called),
                      "unexecuted_top_level_definitions": missing, "remote_calls": 0,
                      "office_execution": "mocked converters; real native DOCX parsing", "entrypoints": ["ingest_document.extract_doc_text", "ingest_inbox.read_document_preview"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
