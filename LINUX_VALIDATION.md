# Linux 0.22 validation

Verified on 2026-11-03 against upstream commit
`17adee8541b77bad83f70baab813530ada03f751`, using Ubuntu 24.04,
Python 3.12.3, uv 0.11.28, LibreOffice 24.2.7.2 and installed Noto CJK fonts.
This is a community Linux edition; it is not upstream compatibility certification.

**Status: draft contribution; complete regression is blocked.** The Linux
release profile and targeted portability checks pass, but the complete native
profile still has eight failures. Each failure was minimally reproduced using
the original test on an isolated, unchanged checkout of the pinned upstream
revision. Relevant code and test files are identical to upstream. This evidence
does not turn the failures into passes or establish release readiness. No
business, authority, graph-policy or transaction rule was changed to bypass them.

## Executed gate

| Check | Observed result |
| --- | --- |
| Frozen dependencies | `uv sync --frozen --all-extras` succeeded; no lockfile change. |
| Doctor | All six profiles passed their required checks; only the expected optional model-configuration warning remained. |
| Engineering graph | 359 nodes, 683 edges, 22 capabilities and 5 contracts validated. |
| Ordered release profile | 19/19 commands passed, including the original 17 in the original order. |
| Complete native profile | 103/111 command invocations passed; 8 failed, as detailed below. |
| Omitted manual-entry supplement | 31 exact upstream test functions executed in separate processes: 28 passed, 3 failed; original assertions retained. |
| Synthetic native formats | 8/8 formats passed; 22/22 required checks passed; all source-file SHA-256 values stayed unchanged. |
| Real rendering | All five native `--render` entry points passed: science exhibit, science exhibit workflow, presentation runtime, presentation state and presentation delivery. |
| Public packaging | The unmodified upstream public builder verified the clean export before delivery. |

## Unresolved native failures

| Original command | Observed blocker on both candidate and unchanged upstream |
| --- | --- |
| `.scripts/test_code_library.py` | Public synthetic catalog lacks the real-paper candidate expected by the integration assertion. |
| `.scripts/test_playbook_dispatch.py` | Required playbook fixture is absent from the public export. |
| `.scripts/test_private_ingest.py` | Legacy-PDF companion backfill triggers `legacy PDF staged sidecar mismatch`; root cause beyond this integrity guard is not certified. |
| `.scripts/test_private_reingest.py` | Self-edge test expects a `ValueError` that the current implementation does not raise. |
| `.scripts/test_prompt_audit.py` | Test expects 14 tool definitions; current upstream defines 18. |
| `.scripts/test_retrieval_benchmark.py` | Historical manifest references Wiki fixtures absent from the public export. |
| `.scripts/test_workspace_state.py` | Public release lacks `projects/_templates/research`; copying it raises `FileNotFoundError`. |
| `dsh/test_semantic_recovery_agent.py` | Test replaces the API recovery agent without selecting the API backend; default Agent handoff returns `Agent task prepared`. |

The separate omitted-entry supplement found three further failures. In
`.scripts/test_ingest_pipeline.py`: the conference-prefill fixture does not
create the parent directory for its temporary SQLite database, and the
keyword-hub test calls the removed `graph_lib.add_child_edge` API. In
`.scripts/test_wg.py`, the neighbor-budget test expects a `data` field absent
from the current response envelope (`KeyError: 'data'`). All three were
also minimally reproduced using the original functions on unchanged upstream;
neither failure is counted among the eight command failures above. These
unresolved cases are additional blockers to complete regression acceptance.

The initial supplement and format-helper attempts stopped before executing any
cases because their strict source-inventory guards found a candidate-only
runtime database already present before the frozen gate. Its bytes, metadata
and original failed logs were retained outside the public source; after exact
path/hash and non-use checks, it was quarantined. The unchanged helpers then
ran against the same controlled source in a fresh retry. No inventory guard or
upstream assertion was relaxed, and this database is not part of the delivery.
That first supplement run passed 26/31 functions; three import-time tokenizer
downloads were blocked by the offline guard, alongside the two upstream
failures. The public tokenizer data was then supplied in an isolated cache and
verified against tiktoken's built-in SHA-256. A fresh run passed 28/31 with zero
blocked attempts; the three upstream failures remain red. The successful format
canary was not repeated for this cache-only correction.

The supplement covers the 31 functions omitted by nine upstream handwritten
entry points. It does not replace those entry points or alter their assertions.
One `capsys` fixture uses a reviewed equivalent stdout/stderr capture adapter;
the remaining functions need no fixture. Static definition counts are not
reported as executed tests or branch coverage. Native JSON output retains the
last 4,000 characters per command, rather than a complete per-test transcript.

## Format and render evidence

The original synthetic fixtures cover DOCX, DOC, PPTX, XLS, XLSX, PDF, TXT and
Markdown. Word checks include body/table order, referenced headers/footers and
notes, source preservation, bounded conversion and malformed inputs. The real
legacy-DOC fixture was converted by LibreOffice, then read through the shared
OOXML parser. Optional antiword/catdoc alone do not establish equivalent fidelity.

PPTX checks exercise presentation order, text/tables, speaker notes, native
schema, page hashes, actual local rendering and resume receipts. Inbox preview
and formal extraction use the same native reader. Hidden pages, groups,
SmartArt and animation fidelity are not covered by this synthetic canary.
Spreadsheet checks distinguish saved cached values from formulas; formulas are
not recalculated. PDF checks exercise local text reading and rendered pages;
managed PDF extraction, provider parsing, OCR and semantic ingestion were not run.

Linux font selection and actual ascent/descent fix the observed CJK clipping
while preserving text, physical dimensions, font sizes, 1.3 line advance and the
strict complete-text bounding-box tolerance. Native render checks passed and
two CJK/mixed-script previews received visual inspection. Presentation runtime
still reports font equivalence as `not_asserted`: Linux Latin font substitution
is not full cross-platform visual identity.

## Conditional coverage and limits

The native `all` profile discovers scripts, not every function in every script.
External-data-dependent CV/experience/directory checks and unavailable legacy
visual templates may skip upstream optional cases; Git-dependent preflight
checks can skip in an archive without Git metadata. Passing commands therefore
do not mean those optional datasets or every branch were exercised. The
separate five `--render` runs cover the native opt-in rendering boundary.

The successful native-format run and final 31-function supplement attempt used
Python socket and subprocess guards with zero forbidden attempts. The initial
tokenizer-cache failures remain in the retained evidence. These guards are not an OS
network sandbox. All fixtures, caches and runtime environments were isolated.
No model/provider/MinerU call, paid workflow, arbitrary-book ingest, production
service, existing private knowledge instance or education-system integration
is part of this validation. Fresh local resume receipts do not establish that
old instance transactions can resume across versions.

## Identity and retained receipts

The tested snapshot had 664 controlled files. Its inventory identity is
`a2e84a88cbdad622349f006296b111bc246655539200475269f3997c31f95cb4`;
the frozen receipt byte hash is `5c303b2f43cd6ea5864ea4d1c57dc769eef67568b58cc01e01f635c49b248721`.
After the gate, only Linux status/setup/verification documentation and deterministic public
provenance were finalized. Executable source, tests, dependencies and profiles
remain byte-for-byte identical to the tested snapshot. The native
`RELEASE_PROVENANCE.json` binds the final public payload; an external complete
inventory also binds every final file and executable mode without self-reference.

Retained server-side evidence (kept outside the public source) includes the
complete command summary, original failed baselines, targeted repair results,
native conditional output, synthetic sources/renders and independent reviews.
The private education regression checklist is not included in this distribution.

| Receipt | SHA-256 |
| --- | --- |
| Original Linux gate (failed, retained) | `f9669229f4584766607fdf43221245c711125a9db85923520e3f381d52ec19fa` |
| Native format canary | `63215063bd908f6b5aa811daa2250a4817883150cd19d472f5bfd629e9cf5e8a` |
| Omitted-entry supplement | `f79c00ab5cdb3c9a711f24239639658517203a26ee27a672c0d9bdb69e7def07` |
| Quarantine and first follow-up (failed supplement retained) | `739d600805040329ef2a7c5974b271f41d5993d50801aa5d77a9d2fc602e6593` |
| Tokenizer cache and final supplement attempt | `0ca467e97204b1256d28dd592925a285c233f03a26962ccf26e43cc8c612e3d9` |
| Two omitted upstream failure reproductions | `58cf9662d1b49b7d37b195e7bd9b0b329d8f238b0efc27d3923d604ac0b384a2` |
| Omitted neighbor-budget upstream failure reproduction | `15eab1f2d0c2c6ba3f261ac06b0ba285523b85941a6f0677899f355f825c0861` |
| Five upstream failure reproductions | `630ae5ee43f64a2bd6f5873d04b8904d1c58ff56844dcba3922c1f70fc147dfa` |
| Three upstream failure reproductions | `040a4e8fc8896280e57a89dc492ac9fbd1b7e5f3f8431238e8e7dbb4fbb734dc` |

Reproduction commands and dependency boundaries are in
[operations/LINUX.md](operations/LINUX.md). The extra legacy-XLS fixture writer
`xlwt==1.3.0` was installed in a separate fixture directory, not the locked
runtime or public source.

To supply that fixture dependency for a full native run without changing the
project lockfile, use `uv run --frozen --all-extras --with xlwt==1.3.0 ran-asks test all`.
