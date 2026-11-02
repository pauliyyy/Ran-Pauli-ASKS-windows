#!/usr/bin/env python3
"""Platform-neutral text extraction for Word documents."""
from __future__ import annotations

import posixpath
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path
from io import BytesIO
from xml.etree import ElementTree

import platform_compat


WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
STRICT_WORD_NS = "http://purl.oclc.org/ooxml/wordprocessingml/main"
STRICT_OFFICE_REL_NS = "http://purl.oclc.org/ooxml/officeDocument/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
W = f"{{{WORD_NS}}}"
R = f"{{{OFFICE_REL_NS}}}"
PR = f"{{{PACKAGE_REL_NS}}}"


MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
MC = f"{{{MC_NS}}}"


class _UnsupportedAlternateContent(ValueError):
    """The native reader cannot select a supported, explicit OOXML branch."""


def _parse_word_xml(data: bytes) -> tuple[ElementTree.Element, set[ElementTree.Element]]:
    """Keep in-scope Requires bindings for the Word namespaces we implement."""
    scopes: list[dict[str, str]] = [{}]
    pending: dict[str, str] = {}
    understood_choices: set[ElementTree.Element] = set()
    parser = ElementTree.iterparse(BytesIO(data), events=("start-ns", "start", "end"))
    for event, value in parser:
        if event == "start-ns":
            prefix, namespace = value
            pending[prefix or ""] = namespace
        elif event == "start":
            current = {**scopes[-1], **pending} if pending else scopes[-1]
            scopes.append(current)
            pending = {}
            if value.tag == f"{MC}Choice":
                required = value.get("Requires", "").split()
                if required and all(current.get(prefix) in {WORD_NS, STRICT_WORD_NS} for prefix in required):
                    understood_choices.add(value)
        else:
            scopes.pop()
    return parser.root, understood_choices


def _active_children(container: ElementTree.Element, understood_choices=frozenset()):
    for child in container:
        if child.tag == f"{MC}AlternateContent":
            branch = next((node for node in child if node.tag == f"{MC}Choice" and node in understood_choices), None)
            if branch is None:
                branch = child.find(f"{MC}Fallback")
            if branch is None:
                raise _UnsupportedAlternateContent("OOXML alternate content has no supported choice or fallback")
            yield from _active_children(branch, understood_choices)
        else:
            yield child


def _active_elements(container: ElementTree.Element, understood_choices=frozenset()):
    yield container
    for child in _active_children(container, understood_choices):
        yield from _active_elements(child, understood_choices)


def _paragraph_text(paragraph: ElementTree.Element, w: str = W, understood_choices=frozenset()) -> str:
    pieces: list[str] = []
    for element in _active_elements(paragraph, understood_choices):
        if element.tag == f"{w}t":
            pieces.append(element.text or "")
        elif element.tag == f"{w}tab":
            pieces.append("\t")
        elif element.tag in {f"{w}br", f"{w}cr"}:
            pieces.append("\n")
        elif element.tag in {f"{w}noBreakHyphen", f"{w}softHyphen"}:
            pieces.append("-")
    return "".join(pieces)


def _container_lines(container: ElementTree.Element, w: str = W, understood_choices=frozenset()) -> list[str]:
    lines: list[str] = []
    for child in _active_children(container, understood_choices):
        if child.tag == f"{w}p":
            lines.append(_paragraph_text(child, w, understood_choices))
        elif child.tag == f"{w}tbl":
            for row in (node for node in _active_children(child, understood_choices) if node.tag == f"{w}tr"):
                cells: list[str] = []
                for cell in (node for node in _active_children(row, understood_choices) if node.tag == f"{w}tc"):
                    cell_lines = _container_lines(cell, w, understood_choices)
                    cells.append("\n".join(cell_lines).strip())
                lines.append("\t".join(cells))
        else:
            # Content controls and custom XML wrappers may contain ordinary
            # paragraphs or tables. Descend through the wrapper without
            # flattening table cells into unrelated body lines.
            lines.extend(_container_lines(child, w, understood_choices))
    return lines


def _document_relationships(
    archive: zipfile.ZipFile, names: set[str]
) -> dict[str, tuple[str, str]]:
    rels_path = "word/_rels/document.xml.rels"
    if rels_path not in names:
        return {}
    try:
        root = ElementTree.fromstring(archive.read(rels_path))
    except (KeyError, ElementTree.ParseError):
        return {}

    relationships: dict[str, tuple[str, str]] = {}
    for relationship in root.findall(f"{PR}Relationship"):
        if relationship.get("TargetMode", "").casefold() == "external":
            continue
        rel_id = relationship.get("Id", "")
        rel_type = relationship.get("Type", "").rsplit("/", 1)[-1]
        target = relationship.get("Target", "")
        if not rel_id or rel_type not in {"header", "footer", "footnotes", "endnotes"}:
            continue
        if target.startswith("/"):
            continue
        part = posixpath.normpath(posixpath.join("word", target))
        if part == "word" or not part.startswith("word/") or part not in names:
            continue
        relationships[rel_id] = (rel_type, part)
    return relationships


def _referenced_parts(
    body: ElementTree.Element,
    relationships: dict[str, tuple[str, str]],
    *,
    w: str = W,
    r: str = R,
    understood_choices=frozenset(),
) -> list[tuple[str, str]]:
    parts: list[tuple[str, str]] = []
    seen: set[str] = set()
    for reference in _active_elements(body, understood_choices):
        if reference.tag not in {f"{w}headerReference", f"{w}footerReference"}:
            continue
        rel_id = reference.get(f"{r}id", "")
        relationship = relationships.get(rel_id)
        if relationship is None or relationship[1] in seen:
            continue
        seen.add(relationship[1])
        parts.append(relationship)
    return parts


def _referenced_note_ids(
    body: ElementTree.Element, kind: str, *, w: str = W, understood_choices=frozenset()
) -> set[str]:
    return {
        reference.get(f"{w}id", "")
        for reference in _active_elements(body, understood_choices)
        if reference.tag == f"{w}{kind}Reference" and reference.get(f"{w}id") is not None
    }


def extract_docx_text(path: str | Path) -> str:
    """Extract visible document text from OOXML without host tools."""
    source = Path(path)
    sections: list[str] = []
    try:
        with zipfile.ZipFile(source) as archive:
            names = set(archive.namelist())
            if "word/document.xml" not in names:
                return ""
            document, document_choices = _parse_word_xml(archive.read("word/document.xml"))
            if document.tag.startswith("{"):
                word_namespace = document.tag[1:].split("}", 1)[0]
            else:
                word_namespace = ""
            if word_namespace not in {WORD_NS, STRICT_WORD_NS}:
                return ""
            office_rel_namespace = (
                STRICT_OFFICE_REL_NS
                if word_namespace == STRICT_WORD_NS else OFFICE_REL_NS
            )
            w = f"{{{word_namespace}}}"
            r = f"{{{office_rel_namespace}}}"
            body = document.find(f"{w}body")
            if body is None:
                return ""

            relationships = _document_relationships(archive, names)
            parts = [("document", "word/document.xml")]
            parts.extend(_referenced_parts(body, relationships, w=w, r=r, understood_choices=document_choices))
            for kind in ("footnotes", "endnotes"):
                part = next((
                    target for rel_type, target in relationships.values()
                    if rel_type == kind
                ), None)
                if part:
                    parts.append((kind, part))

            note_ids = {
                "footnotes": _referenced_note_ids(body, "footnote", w=w, understood_choices=document_choices),
                "endnotes": _referenced_note_ids(body, "endnote", w=w, understood_choices=document_choices),
            }
            for kind, part in parts:
                root, part_choices = ((document, document_choices) if kind == "document"
                                      else _parse_word_xml(archive.read(part)))
                if kind == "document":
                    containers = [body]
                elif kind in note_ids:
                    ids = note_ids[kind]
                    containers = [
                        note for note in _active_children(root, part_choices)
                        if note.get(f"{w}id", "") in ids
                    ]
                else:
                    containers = [root]
                lines: list[str] = []
                for container in containers:
                    lines.extend(_container_lines(container, w, part_choices))
                section = "\n".join(lines).strip()
                if section:
                    sections.append(section)
    except (OSError, KeyError, ElementTree.ParseError, zipfile.BadZipFile, _UnsupportedAlternateContent):
        return ""
    text = "\n\n".join(sections)
    return f"{text}\n" if text else ""


def _run_text_command(command: list[str], timeout: int = 120) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


def _extract_doc_with_soffice(path: Path, soffice: Path, timeout: float = 180) -> str:
    with tempfile.TemporaryDirectory(prefix="asks-doc-text-") as temp_dir:
        workspace = Path(temp_dir)
        output_dir = workspace / "output"
        profile_dir = workspace / "profile"
        output_dir.mkdir()
        profile_dir.mkdir()
        command = [
            str(soffice),
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            str(output_dir),
            str(path),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                env=platform_compat.soffice_environment(soffice),
            )
        except (OSError, subprocess.SubprocessError):
            return ""
        converted = output_dir / f"{path.stem}.docx"
        if result.returncode != 0 or not converted.is_file():
            return ""
        # The text export drops headers and footers from genuine legacy DOC.
        # Convert only inside this private temporary workspace and reuse the
        # native OOXML reader directly, without re-entering the fallback chain.
        return extract_docx_text(converted)


def _remaining_timeout(deadline: float | None, limit: float) -> float:
    """Bound a converter invocation by both its own cap and the shared deadline."""
    if deadline is None:
        return limit
    return min(limit, max(0.0, deadline - time.monotonic()))


def extract_legacy_doc_text(path: str | Path, timeout: float | None = None) -> str:
    """Extract legacy DOC text within an optional total converter deadline."""
    source = Path(path)
    deadline = None if timeout is None else time.monotonic() + max(0.0, timeout)
    if _remaining_timeout(deadline, 120) <= 0:
        return ""
    textutil = platform_compat.find_executable("textutil")
    if textutil:
        remaining = _remaining_timeout(deadline, 120)
        if remaining <= 0:
            return ""
        text = _run_text_command([
            str(textutil), "-convert", "txt", "-stdout", str(source),
        ], timeout=remaining)
        if text:
            return text

    if _remaining_timeout(deadline, 180) <= 0:
        return ""
    soffice = platform_compat.find_soffice()
    if soffice:
        remaining = _remaining_timeout(deadline, 180)
        if remaining <= 0:
            return ""
        text = _extract_doc_with_soffice(source, soffice, timeout=remaining)
        if text:
            return text

    for name in ("antiword", "catdoc"):
        if _remaining_timeout(deadline, 120) <= 0:
            return ""
        converter = platform_compat.find_executable(name)
        if converter:
            remaining = _remaining_timeout(deadline, 120)
            if remaining <= 0:
                return ""
            text = _run_text_command([str(converter), str(source)], timeout=remaining)
            if text:
                return text
    return ""


def extract_word_text(
    path: str | Path, max_chars: int | None = None, *, timeout: float | None = None
) -> str:
    """Extract Word text; timeout bounds the DOC converter chain, not OOXML parsing."""
    source = Path(path)
    suffix = source.suffix.casefold()
    if suffix == ".docx":
        text = extract_docx_text(source)
    elif suffix == ".doc":
        text = extract_legacy_doc_text(source, timeout=timeout)
    else:
        return ""
    if max_chars is None:
        return text
    return text[:max(0, max_chars)]
