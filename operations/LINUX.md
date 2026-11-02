# Linux edition: ASKS 0.22

This independently maintained community edition is pinned to Ran-ASKS 0.22.0,
upstream commit `17adee8541b77bad83f70baab813530ada03f751`. The distribution
directory is `ASKS_0.22_linux`. `VERSION` and Python package metadata retain the
upstream `0.22.0`; [DOWNSTREAM.md](../DOWNSTREAM.md) identifies this Linux edition.
It does not install or update an education web application or production service.

## Ubuntu setup

The verified host uses Ubuntu 24.04, Python 3.12 and LibreOffice 24.2. Install the
system dependencies appropriate to the formats you use:

```bash
sudo apt-get install python3.12-venv libreoffice-writer libreoffice-impress \
  libreoffice-calc fontconfig fonts-noto-cjk poppler-utils tesseract-ocr
uv sync --frozen --all-extras
uv run ran-asks doctor --profile release
uv run ran-asks doctor --profile office
uv run ran-asks doctor --profile visual
uv run ran-asks test release
```

The repository CI pins uv 0.11.28. Core usage needs fewer extras; `office`, `pdf`,
`analysis` and `visual` are declared in `pyproject.toml`. `xlwt==1.3.0` is only a
synthetic legacy-XLS test-fixture dependency, not a runtime requirement. The
standalone regression canary supplies it outside the locked runtime environment.
No model key is needed for deterministic tests or local format/render checks.
The doctor's optional model-configuration warning is expected without a `.env`.
Configure model services only when intentionally running an API workflow, using
the upstream instructions. Agent mode and API mode retain their upstream roles.

## Word text extraction

Document intake and inbox classification share one deterministic Word reader.
DOCX is read directly with body/table ordering, referenced headers, footers and
notes, and one supported OOXML Choice or Fallback branch. Legacy DOC uses an
isolated LibreOffice profile to convert to temporary DOCX, then the same reader;
this retains header/footer content that a plain-text conversion can lose.
macOS `textutil` and optional antiword/catdoc fallbacks remain available.
The tested synthetic legacy-DOC fixture retained its checked text, ordering and
header/footer content after LibreOffice conversion; this is not a general fidelity
guarantee, and fallback tools alone do not establish equivalent extraction.

The preview keeps its original 30-second total conversion deadline. Formal Word
extraction now has a 120-second total conversion deadline; the upstream formal
entry had no timeout. Exhausting the deadline prevents another converter from
starting. The original source is never replaced. Unsupported or failed parsing
retains the original caller's failure behavior; extraction success is not an
ingestion commit or a scientific correctness verdict.

PPTX inbox previews reuse the upstream native PPTX reader used by formal
extraction, preserving presentation order, native text and tables. They do not
require pandoc or a second parser; malformed previews retain the empty-result
failure contract.

## Fonts and rendering

New Linux exhibits and presentation probes use `Noto Sans CJK SC`. macOS retains
the original `Heiti SC` exhibit and `PingFang SC` presentation defaults; Windows
selection uses `Microsoft YaHei`. `ASKS_CJK_FONT` can choose another default;
an explicit CLI font or an already saved project font keeps precedence and
continues to fail if unavailable. Install the requested family rather than
silently rewriting a saved project's layout.

Font capacity and native text-frame insets use the installed font collection's
actual metrics. The strict complete-text bounding-box check, physical dimensions,
text, font sizes and 1.3 line advance remain intact. LibreOffice discovery keeps
launcher symlinks and caller fontconfig settings. On a headless server, retain
the generated files for inspection; no desktop session is required to convert.
Presentation runtime still reports font equivalence separately: a Linux Latin
font substitution must not be presented as full cross-platform visual identity.

## Verification and upgrade boundary

`test release` retains all 17 upstream commands in order and then runs the two
Linux adapter regressions. `test all` discovers native test-script entry points;
handwritten entry points can omit test functions. The observed full run passed
103/111 commands, with eight failures also reproduced on unchanged upstream.
See the verification record for the separate 31-function supplement and limits.
Real rendering is opt-in upstream and must be checked separately, for example:

```bash
uv run python .scripts/test_science_exhibit.py --render
uv run python .scripts/test_science_exhibit_workflow.py --render
uv run python .scripts/test_presentation_runtime.py --render
uv run python .scripts/test_presentation_state.py --render
uv run python .scripts/test_presentation_delivery.py --render
```

The exact executed results, omitted-entry supplement and conditional coverage
are recorded in [LINUX_VALIDATION.md](../LINUX_VALIDATION.md). Local synthetic
formats and render canaries do not establish model quality, remote parsing,
arbitrary-book ingestion or education-system integration.

KU maintenance, Gallery, Raw/Wiki/Graph authority, advisory review, validators,
Agent/API separation and managed transaction rules come from pinned 0.22.0.
This edition does not transplant education-specific book compilers, evidence
sidecars, host adapters or resume fingerprints from a previous system release.
Do not copy an old instance's mutable state over the new source tree or assume
an older paused transaction is resumable solely because the source was upgraded.
Back up an existing instance before a deliberate migration under upstream rules.
