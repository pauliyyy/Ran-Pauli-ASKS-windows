#!/usr/bin/env python3
"""Compact routed query/ingest presentation while preserving source instructions.

No source document is rewritten. Literal bytes and instruction words stay intact;
only redundant presentation and exact already-inlined source overlap are reduced.
"""
import re


def protected_inline_parts(line):
    # Inline code and links remain byte-exact. An unmatched code delimiter
    # makes the whole line literal, so this renderer fails conservatively.
    spans = []
    i = 0
    while i < len(line):
        if line[i] == "`" and (i == 0 or line[i - 1] != "\\"):
            end = i + 1
            while end < len(line) and line[end] == "`":
                end += 1
            marker = line[i:end]
            close = re.search(r"(?<!`)" + re.escape(marker) + r"(?!`)", line[end:])
            if close is None:
                return [(True, line)]
            stop = end + close.end()
            spans.append((i, stop))
            i = stop
        else:
            i += 1
    for match in re.finditer(r"!?\[[^\]\n]*\]\([^\n)]*\)|!?\[[^\]\n]*\]\[[^\]\n]*\]|<https?://[^>\n]*>", line):
        spans.append(match.span())
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    result = []
    offset = 0
    for start, end in merged:
        result.append((False, line[offset:start]))
        result.append((True, line[start:end]))
        offset = end
    result.append((False, line[offset:]))
    return result


def compact_line(line):
    parts = protected_inline_parts(line)
    # Literal spans and their delimiters stay intact. Strong emphasis is
    # presentation only: the complete words and punctuation are retained.
    for index, (protected, text) in enumerate(parts):
        if not protected:
            text = re.sub(r"(?<![\\*A-Za-z0-9_])\*\*([^\s*](?:[^*\n]*[^\s*])?)\*\*(?![*A-Za-z0-9_])",
                          lambda match: match.group(1) if re.search(r"[\u3400-\u9fff]", match.group(1)) else match.group(0), text)
            if index + 1 < len(parts) and parts[index + 1][1].startswith("`"):
                text = re.sub(r"(?<=[\u3400-\u9fff]) +$", "", text)
            if index and parts[index - 1][1].startswith("`"):
                text = re.sub(r"^ +(?=[\u3400-\u9fff])", "", text)
            parts[index] = (protected, text)
    transformed = "".join(text for _, text in parts)
    # Compact table cells only at pipes outside protected inline code/links.
    stripped = transformed.lstrip(" ")
    if stripped.startswith("|") and stripped.endswith("|"):
        pipes = []
        offset = 0
        for protected, text in protected_inline_parts(transformed):
            if not protected:
                pipes.extend(offset + m.start() for m in re.finditer(r"(?<!\\)\|", text))
            offset += len(text)
        if len(pipes) >= 2:
            cells = [transformed[a + 1:b].strip(" \t") for a, b in zip(pipes, pipes[1:])]
            if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
                cells = [(":" if cell.startswith(":") else "") + "---" + (":" if cell.endswith(":") else "") for cell in cells]
            transformed = transformed[:pipes[0]] + "|" + "|".join(cells) + "|"
    return transformed



def _has_unclosed_inline_run(line):
    """Find a possible multiline code opener using exact backtick runs.

    Outside code, an odd number of preceding backslashes escapes an opener.
    Inside code, backslashes are literal and an equal-length run closes it.
    """
    opened = None
    for match in re.finditer(r"`+", line):
        size = len(match.group())
        if opened is not None:
            if size == opened:
                opened = None
            continue
        before = match.start()
        while before and line[before - 1] == "\\":
            before -= 1
        escaped = (match.start() - before) % 2 == 1
        if escaped and size > 1:
            # CommonMark escapes one backtick, not the entire run. Rather than
            # interpret the remaining run, preserve this whole paragraph.
            return True
        if not escaped:
            opened = size
    return opened is not None


def _multiline_inline_line_starts(text):
    """Conservatively protect whole paragraphs with a possible spanning run.

    A line-local renderer cannot safely interpret the interior lines of a code
    span. If any line leaves an inline run open, retain its complete paragraph
    byte-for-byte in both presentation and provenance scanning. Blank lines and
    real fenced blocks delimit paragraphs; indented continuations do not.
    Unmatched runs use the same safe fallback, without affecting later blocks.
    """
    protected = set()
    paragraph = []
    possible_span = False
    fence = None
    offset = 0

    def finish_paragraph():
        nonlocal possible_span
        if possible_span:
            protected.update(paragraph)
        paragraph.clear()
        possible_span = False

    for line in text.splitlines(keepends=True):
        raw = line.rstrip("\r\n")
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", raw)
        if fence is not None:
            if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence) and not marker.group(2).strip():
                fence = None
        elif marker:
            finish_paragraph()
            fence = marker.group(1)
        elif not raw.strip():
            finish_paragraph()
        else:
            paragraph.append(offset)
            possible_span = possible_span or _has_unclosed_inline_run(raw)
        offset += len(line)
    finish_paragraph()
    return protected


def compact_markdown(text):
    protected_paragraphs = _multiline_inline_line_starts(text)
    offset = 0
    output = []
    changes = []
    fence = None
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        ending = "\n" if line.endswith("\n") else ""
        raw = line[:-1] if ending else line
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", raw)
        if marker:
            if fence is None:
                fence = marker.group(1)
            elif marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence) and not marker.group(2).strip():
                fence = None
            new = raw
        elif (offset in protected_paragraphs or fence is not None or raw.startswith("    ") or raw.lstrip().startswith(">")
              or "\\" in raw or "](" in raw or "][" in raw
              or re.search(r"加粗|粗体|bold|strong", raw, re.I)):
            new = raw
        else:
            new = compact_line(raw)
        # No trailing-whitespace removal: two-space Markdown hard breaks stay.
        if new != raw:
            changes.append({"line": number, "before": raw, "after": new})
        output.append(new + ending)
        offset += len(line)
    rendered = "".join(output)
    return rendered, changes



def routed_header_matches(text, pattern):
    # A source document may itself demonstrate router headers in literal code.
    # Only generated top-level, non-literal headers can carry provenance.
    starts = set()
    protected_paragraphs = _multiline_inline_line_starts(text)
    fence = None
    offset = 0
    for line in text.splitlines(keepends=True):
        raw = line.rstrip("\r\n")
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", raw)
        if marker:
            if fence is None:
                fence = marker.group(1)
            elif marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence) and not marker.group(2).strip():
                fence = None
        elif offset not in protected_paragraphs and fence is None and not raw.startswith("    ") and not raw.lstrip().startswith(">"):
            starts.add(offset)
        offset += len(line)
    return [match for match in pattern.finditer(text) if match.start() in starts]


def compact_query_wrappers(text):
    pattern = re.compile(r"^--- operations/QUERY\.md#md:[^\n]+ (\[L\d+-L\d+\]) ---\n", re.M)
    matches = routed_header_matches(text, pattern)
    if not matches:
        return text
    chunks = []
    position = 0
    for index, match in enumerate(matches):
        chunks.append(text[position:match.start()])
        if index == 0:
            chunks.append("[来源 operations/QUERY.md；以下按原行范围分段]\n")
        chunks.append(match.group(1) + "\n")
        position = match.end()
    chunks.append(text[position:])
    return "".join(chunks)


def deduplicate_contained_sections(text):
    pattern = re.compile(r"^--- (?P<file>[^\n]+?)#(?P<locator>md:.*?) \[L(?P<start>\d+)-L(?P<end>\d+)\] ---\n", re.M)
    matches = routed_header_matches(text, pattern)
    seen = []
    chunks = []
    changes = []
    position = 0
    for index, match in enumerate(matches):
        stop = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end():stop]
        start_line, end_line = int(match.group("start")), int(match.group("end"))
        owner = next((prior for prior in seen
                      if prior["file"] == match.group("file")
                      and prior["start"] <= start_line and end_line <= prior["end"]
                      and body.strip() in prior["body"]), None)
        chunks.append(text[position:match.end()])
        if owner is not None:
            replacement = "（本段全部原文已完整包含于此前同源 [L" + str(owner["start"]) + "-L" + str(owner["end"]) + "]；沿用全部约束。）\n\n"
            chunks.append(replacement)
            changes.append({"label": match.group(0).strip(), "file": match.group("file"), "source_range": [start_line, end_line], "included_in_range": [owner["start"], owner["end"]], "removed_duplicate_body": body, "replacement": replacement})
        else:
            chunks.append(body)
            seen.append({"file": match.group("file"), "start": start_line, "end": end_line, "body": body})
        position = stop
    chunks.append(text[position:])
    return "".join(chunks), changes


def render_routed_text(text, *, shared_query_source=False):
    """Render an already selected route; full source hits remain the authority."""
    text, _duplicates = deduplicate_contained_sections(text)
    text, _presentation = compact_markdown(text)
    if shared_query_source:
        text = compact_query_wrappers(text)
    return text
