---
schema: asks-community-downstream-record-v1
name: "AIsystem-Ran-Pauli-ASKS-Linux"
status: community
upstream_repository: "https://github.com/ranshiju/Ran-ASKS"
upstream_version: "0.17.0"
downstream_version: "0.17.0-linux.1"
upstream_commit: "8eef1cd0dbd81d087573b225d1d41d0808f085e0"
maintainers:
  - name: "cnuchw"
    contact: "local deployment owner"
---

# AIsystem Linux Downstream Record

> Community downstream used by the AIsystem teaching platform. It is
> independently maintained and is not an official Ran-ASKS distribution.

## Purpose And Ownership

- **Domain or task:** Linux-hosted, per-teacher knowledge compilation and
  retrieval for the AI-assisted teaching system.
- **Repository owner:** The local AIsystem deployment owner.
- **Issue tracker:** The local AIsystem development workspace.
- **Release policy:** Rebase onto an exact upstream commit in an isolated work
  tree, reapply reviewed Linux/integration patches, and deploy only after the
  deterministic ASKS and host integration suites pass.

## Upstream Baseline

- Public upstream version: `0.17.0`
- Public upstream commit: `8eef1cd0dbd81d087573b225d1d41d0808f085e0`
- Previous accepted downstream baseline: upstream `0.10.0` commit
  `0e87e3bb295f57419c6b7bbc8a9b497a44e83526`, archived with host V0.5.14
- Migration date: `2026-10-16`
- Linux downstream version: `0.17.0-linux.1`
- Complete adaptation history and conflict outcomes: `LINUX_CHANGELOG.md`
- Pre-migration backup: `AIsystem/.asks-backups/Ran-Pauli-ASKS-Linux-v0.6-linux-20260927.tar.gz`
- Backup SHA-256: `1f64b368d3f703921587c28857451db23d24372fad5a5eca32cfcbbfa5336891`

The retained `RELEASE_PROVENANCE.json` describes the pristine upstream public
release input. Its payload hash does not attest this modified downstream tree;
this record is the authority for the downstream baseline and modifications.

## Domain Capabilities

- Python 3.12+ on Ubuntu 22.04+ dependency and host-capability preflight.
- Native OOXML DOCX extraction and host-capability fallback for legacy DOC.
- Cross-platform LibreOffice discovery, child-process font configuration,
  desktop opening, WSL path handling, and recoverable system trash.
- Collision-resistant ingestion transaction identifiers for concurrent teacher
  imports.
- Strict teaching-system ingestion completion semantics.
- Build-only DSH session journals inside each teacher revision's private staging
  directory; published revisions and oral-exam retrieval never depend on them.
- Stage-specific timeout reporting for MinerU extraction, model generation,
  embedding, and the outer build deadline, with a bounded 180-second model
  transport timeout for knowledge compilation.
- Unicode-stable paper-author identity matching for strict ingestion. NFKD
  comparison tolerates OCR loss or decomposition of diacritics while the
  first source spelling remains unchanged in stored and displayed metadata.
- Pristine per-teacher graphs initialize their empty SQLite schema before
  semantic abbreviation resolution reads the name index; knowledge facts are
  still written only by the normal validated Graph plan/commit stage.
- Physical teacher and revision isolation is owned by the external
  `asks-education-system/current/app`
  host; upstream's single private domain does not replace that boundary.

## Core Files Modified

| Core path | Reason | Disposition | Migration note |
| --- | --- | --- | --- |
| `.scripts/ingest_document.py` | Linux Word extraction and collision-resistant transaction IDs | Retain | Three-way rebased onto the complete v0.17 ingestion pipeline |
| `.scripts/ingest_inbox.py` | Native Word/PPTX classification preview | Retain | Avoids macOS-only tools and unsupported Pandoc PPTX input |
| `.scripts/ingest_meeting.py` | Collision-resistant transaction IDs | Retain | Preserves concurrent import safety |
| `.scripts/wg.py` | Only `completed` and `duplicate_found` are host successes | Retain | Required by the AI education system publication boundary |
| `.scripts/visual_qa.py` | Cross-platform LibreOffice discovery and environment | Retain | Keeps the upstream env/API transport implementation |
| `.scripts/visual_to_editable_ppt.py` | Cross-platform LibreOffice discovery and environment | Retain | No semantic workflow change |
| `.scripts/extractor.py` | PDF page-OCR endpoint and visual-model configuration | Retain | Uses normalized API paths and an optional independent `BLSC_OCR_*` role |
| `.scripts/llm_structured.py` | Specialist endpoint isolation | Retain | Routes generation/proposition roles by normalized endpoint plus model, including independent API paths |
| `.scripts/ingest_paper.py` | Unicode-stable author identity comparison, equivalent-name deduplication, and pristine graph schema bootstrap | Retain | Keeps strict title-author coverage while accepting OCR-equivalent diacritic forms; initializes empty core tables before first-ingest abbreviation lookup without writing facts |
| `.scripts/graph_ingest.py` | Empty graph schema initialization before name resolution | Retain | Read preparation only; facts still require validated plans |
| `dsh/ingest_tools.py` | Extraction failure classification before semantic/graph classification | Retain | Includes upstream code-defect classification |
| `dsh/harness.py` | Private build-only session journal | Retain | Persists typed build events only under the isolated staging `temp/` tree; not used by query or oral exams |
| `.scripts/graph_visualize.py` | Cross-platform desktop opening | Retain | Headless operation remains non-destructive |
| `.scripts/trash_util.py` | Freedesktop/macOS recoverable trash | Retain | Never falls back to permanent deletion |
| `.scripts/hub_split.py` | Python 3.10/3.11 compatible f-string quoting | Propose upstream | Syntax-only compatibility fix |
| `operations/engineering/graph.yaml` | Registers Linux adapters and checks | Retain | Merged with all v0.17 nodes, capabilities, contracts, and links |
| `requirements.txt` | Reproducible Linux runtime dependencies | Retain | Pins upstream-tested PyMuPDF 1.28.0 so the legacy `fitz` shim cannot pollute JSON stdout |

Linux-only implementation and regression files are
`.scripts/document_text.py`, `.scripts/platform_compat.py`,
`.scripts/ubuntu_preflight.py`, `.scripts/test_platform_compat.py`,
`.scripts/test_embed_helper.py`, `operations/UBUNTU.md`, `requirements.txt`, and
`requirements-docling.txt`.

## Declared Protocols And Checks

```text
agent task protocol: agent-task-v1
public host CLI:
  - python3 .scripts/wg.py ingest <path> --keep-source --subproject academic
  - python3 .scripts/wg.py hybrid-recall <query> --intent <intent> --topk <n>
success states:
  - completed
  - duplicate_found
conformance commands:
  - python3 .scripts/test_env_config.py
  - python3 .scripts/test_private_isolation.py
  - python3 .scripts/test_agent_task.py
  - python3 .scripts/test_wg.py
  - python3 .scripts/test_platform_compat.py
  - python3 .scripts/test_ingest_document.py
  - python3 .scripts/test_ingest_meeting.py
  - python3 .scripts/test_ingest_inbox_dispatch.py
  - python3 .scripts/engineering_graph.py validate
```

## Data, Privacy, Security, And License

This engine template contains no teacher knowledge. The host creates separate
physical engine instances for each teacher revision and supplies credentials in
the child process environment. Process values must override repository `.env`
defaults. Remote OCR or PPT visual processing remains opt-in; this downstream
does not silently add remote-upload authorization. Raw, Wiki, graph, receipt,
cache, and rollback state remain inside the owning revision.

## Upstream Candidates

- Collision-resistant document and meeting transaction identifiers.
- Strict `wg.py ingest` outer-envelope completion semantics.
- Python 3.10/3.11 compatible quoting in `hub_split.py`.
- Capability-based Linux/macOS document, LibreOffice, desktop-open, and trash
  adapters.
