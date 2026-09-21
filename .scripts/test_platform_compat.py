#!/usr/bin/env python3
"""Regression checks for Ubuntu/macOS host adapters."""
from __future__ import annotations

import stat
import sys
import tempfile
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

import document_text
import platform_compat
import trash_util
import ubuntu_preflight


def _executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_soffice_resolution_and_environment(tmp: Path) -> None:
    explicit = _executable(tmp / "soffice")
    resolved = platform_compat.find_soffice(
        explicit,
        environ={},
        which=lambda _name: None,
        home=tmp / "home",
    )
    assert resolved == explicit.resolve()

    snap_launcher = _executable(tmp / "snap")
    snap_link = tmp / "libreoffice"
    snap_link.symlink_to(snap_launcher)
    resolved_snap = platform_compat.find_soffice(
        environ={},
        which=lambda name: str(snap_link) if name == "libreoffice" else None,
        home=tmp / "home",
    )
    assert resolved_snap == snap_link.absolute()
    assert resolved_snap != snap_link.resolve()

    bundled = tmp / "runtime/dependencies/bin/override/soffice"
    _executable(bundled)
    config = (
        tmp
        / "runtime/dependencies/native/libreoffice-headless/libreoffice"
        / "LibreOfficeDev.app/Contents/Resources/fontconfig/fonts.conf"
    )
    config.parent.mkdir(parents=True)
    config.write_text("<fontconfig/>", encoding="utf-8")
    env = platform_compat.soffice_environment(bundled, environ={})
    assert env["FONTCONFIG_FILE"] == str(config)
    preserved = platform_compat.soffice_environment(
        bundled, environ={"FONTCONFIG_PATH": "/custom/fonts"}
    )
    assert preserved == {"FONTCONFIG_PATH": "/custom/fonts"}

    app_binary = _executable(
        tmp / "LibreOffice.app/Contents/MacOS/soffice"
    )
    app_config = (
        tmp / "LibreOffice.app/Contents/Resources/fontconfig/fonts.conf"
    )
    app_config.parent.mkdir(parents=True)
    app_config.write_text("<fontconfig/>", encoding="utf-8")
    linked_binary = tmp / "usr/local/bin/soffice"
    linked_binary.parent.mkdir(parents=True)
    linked_binary.symlink_to(app_binary)
    linked_env = platform_compat.soffice_environment(linked_binary, environ={})
    assert linked_env["FONTCONFIG_FILE"] == str(app_config)


def test_linux_and_macos_open_commands(tmp: Path) -> None:
    tools = {
        "xdg-open": _executable(tmp / "xdg-open"),
        "gio": _executable(tmp / "gio"),
        "open": _executable(tmp / "open"),
    }
    resolver = lambda name: str(tools[name]) if name in tools else None
    assert platform_compat.default_open_command(
        "result.html", platform="linux", which=resolver
    ) == [str(tools["xdg-open"].resolve()), "result.html"]
    assert platform_compat.default_open_command(
        "result.html", platform="darwin", which=resolver
    ) == [str(tools["open"].resolve()), "result.html"]

    calls: list[list[str]] = []

    outcomes = iter((1, 0))

    def run(command, **_kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=next(outcomes))

    assert platform_compat.open_with_default_app(
        "result.html", platform="linux", which=resolver, run=run
    )
    assert calls == [
        [str(tools["xdg-open"].resolve()), "result.html"],
        [str(tools["gio"].resolve()), "open", "result.html"],
    ]


def test_wsl_explorer_converts_linux_path(tmp: Path) -> None:
    tools = {
        "explorer.exe": _executable(tmp / "explorer.exe"),
        "wslpath": _executable(tmp / "wslpath"),
        "xdg-open": _executable(tmp / "xdg-open"),
    }
    resolver = lambda name: str(tools[name]) if name in tools else None
    source = tmp / "result.html"
    source.write_text("desktop opener", encoding="utf-8")
    converted_path = r"\\wsl.localhost\Ubuntu\tmp\result.html"
    opened: list[list[str]] = []

    def run(command, **_kwargs):
        if Path(command[0]).name == "wslpath":
            assert command[1:] == ["-w", str(source)]
            return SimpleNamespace(
                returncode=0, stdout=f"{converted_path}\n", stderr=""
            )
        opened.append(command)
        # xdg-open maps explorer.exe's non-zero success to operation-failed.
        return SimpleNamespace(returncode=4, stdout="", stderr="")

    assert platform_compat.open_with_default_app(
        source, platform="linux", which=resolver, run=run
    )
    assert opened == [[str(tools["xdg-open"].resolve()), str(source)]]

    opened.clear()
    resolver_without_xdg = (
        lambda name: str(tools[name])
        if name in {"explorer.exe", "wslpath"} else None
    )

    def explorer_run(command, **_kwargs):
        if Path(command[0]).name == "wslpath":
            return SimpleNamespace(
                returncode=0, stdout=f"{converted_path}\n", stderr=""
            )
        opened.append(command)
        return SimpleNamespace(returncode=1, stdout="", stderr="")

    assert platform_compat.open_with_default_app(
        source, platform="linux", which=resolver_without_xdg, run=explorer_run
    )
    assert opened == [[str(tools["explorer.exe"].resolve()), converted_path]]


def test_ubuntu_preflight_reports_missing_and_ready_tools(tmp: Path) -> None:
    names = (
        "git", "curl", "rg", "tesseract", "soffice",
        "xdg-open", "gio",
    )
    tools = {name: _executable(tmp / name) for name in names}
    resolver = lambda name: str(tools[name]) if name in tools else None

    def run(command, **_kwargs):
        if command[1:] == ["--list-langs"]:
            return SimpleNamespace(returncode=0, stdout="eng\nchi_sim\n", stderr="")
        raise AssertionError(command)

    with patch.object(
        ubuntu_preflight.platform_compat,
        "find_soffice",
        return_value=tools["soffice"],
    ):
        report = ubuntu_preflight.build_report(
            which=resolver,
            environ={},
            platform="linux",
            run=run,
            import_probe=lambda name: (True, name),
            version_info=(3, 10, 0),
            repo=tmp,
        )
    assert report["ready"] is True

    with patch.object(
        ubuntu_preflight.platform_compat,
        "find_soffice",
        return_value=None,
    ):
        missing = ubuntu_preflight.build_report(
            which=lambda _name: None,
            environ={},
            platform="linux",
            run=run,
            import_probe=lambda name: (False, f"missing import {name}"),
            version_info=(3, 9, 0),
            repo=tmp,
        )
    assert missing["ready"] is False
    failed = {item["name"] for item in missing["checks"] if not item["ok"]}
    assert {"python-version", "command:ripgrep", "command:libreoffice"} <= failed


def test_linux_trash_order_system_success_and_project_fallback(tmp: Path) -> None:
    tools = {
        "gio": _executable(tmp / "gio"),
        "trash-put": _executable(tmp / "trash-put"),
        "trash": _executable(tmp / "trash"),
    }
    resolver = lambda name: str(tools[name]) if name in tools else None
    commands = platform_compat.system_trash_commands(
        tmp / "source.txt", platform="linux", which=resolver
    )
    assert [Path(command[0]).name for command in commands] == [
        "gio", "trash-put", "trash",
    ]
    assert commands[0][1] == "trash"

    original_repo = trash_util.REPO
    original_commands = trash_util.platform_compat.system_trash_commands
    original_run = trash_util.subprocess.run
    try:
        trash_util.REPO = tmp / "repo"

        source = tmp / "system-trash.txt"
        source.write_text("recoverable", encoding="utf-8")
        trash_util.platform_compat.system_trash_commands = lambda path: [
            ["gio", "trash", str(path)]
        ]

        def successful_trash(_command, **_kwargs):
            source.unlink()
            return SimpleNamespace(returncode=0)

        trash_util.subprocess.run = successful_trash
        trash_util.trash_path(source)
        assert not source.exists()
        assert not (trash_util.REPO / "temp/trash").exists()

        trash_util.platform_compat.system_trash_commands = lambda _path: []
        trash_util.subprocess.run = original_run
        source = tmp / "fallback.txt"
        source.write_text("recoverable", encoding="utf-8")
        trash_util.trash_path(source)
        assert not source.exists()
        recovered = list((trash_util.REPO / "temp/trash").glob("fallback-*.txt"))
        assert len(recovered) == 1
        assert recovered[0].read_text(encoding="utf-8") == "recoverable"
    finally:
        trash_util.REPO = original_repo
        trash_util.platform_compat.system_trash_commands = original_commands
        trash_util.subprocess.run = original_run


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
        (output_dir / "legacy.txt").write_text("portable text\n", encoding="utf-8")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    try:
        document_text.platform_compat.find_executable = lambda *_names: None
        document_text.platform_compat.find_soffice = lambda: soffice
        document_text.platform_compat.soffice_environment = lambda _path: {
            "LANG": "C.UTF-8"
        }
        document_text.subprocess.run = run
        assert document_text.extract_word_text(source) == "portable text\n"
    finally:
        document_text.platform_compat.find_executable = original_executable
        document_text.platform_compat.find_soffice = original_soffice
        document_text.platform_compat.soffice_environment = original_environment
        document_text.subprocess.run = original_run
    assert output_dirs and all(not path.exists() for path in output_dirs)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="platform-compat-test-") as temp_dir:
        tmp = Path(temp_dir)
        test_soffice_resolution_and_environment(tmp)
        test_linux_and_macos_open_commands(tmp)
        test_wsl_explorer_converts_linux_path(tmp)
        test_ubuntu_preflight_reports_missing_and_ready_tools(tmp)
        test_linux_trash_order_system_success_and_project_fallback(tmp)
        test_docx_structured_text_extraction(tmp)
        test_legacy_doc_uses_soffice_without_persisting_conversion(tmp)
    print("platform compatibility regression: PASS")


if __name__ == "__main__":
    main()
