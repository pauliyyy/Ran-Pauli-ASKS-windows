# Linux edition changes

## 0.22.0 Linux edition — 2026-11-03

- Upgrade the complete upstream source from the Linux branch's 0.17 baseline to
  pinned 0.22.0, including upstream KU maintenance, Gallery and current protocols.
- Replace macOS-only Word calls with shared DOCX parsing and bounded legacy-DOC
  conversion, including headers/footers/notes and explicit OOXML branch handling.
- Keep preview conversion within 30 seconds and bound formal Word conversion
  to 120 seconds; fallback cannot extend the total deadline.
- Reuse the upstream native PPTX parser for inbox previews, preserving slide
  order and table text without a pandoc dependency.
- Use installed platform CJK defaults and actual font metrics for strict native
  render geometry; preserve explicit/saved font rejection and original text.
- Retain the upstream release profile and append two Linux regressions; add a
  Linux-branch CI gate and record actual native, supplemental and render results.
- Deliver independent source only. No education application, production service,
  existing knowledge instance, model key or paid model workflow is changed.

This is a downstream edition of upstream 0.22.0, not an upstream version bump.
Older Linux history remains available in the Git history of the Linux branch.
