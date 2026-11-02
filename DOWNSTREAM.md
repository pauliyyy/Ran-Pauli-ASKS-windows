---
schema: asks-community-downstream-record-v1
name: "ASKS_0.22_linux"
status: community
upstream_repository: "https://github.com/ranshiju/Ran-ASKS"
upstream_version: "0.22.0"
upstream_commit: "17adee8541b77bad83f70baab813530ada03f751"
maintainers:
  - name: "pauliyyy"
    contact: "https://github.com/pauliyyy"
---

# ASKS_0.22_linux

**Draft contribution:** the complete native run passed 103/111 commands. Eight
failures were also reproduced on unchanged upstream; complete regression remains
blocked. See [verification and unresolved cases](LINUX_VALIDATION.md).

Community Linux edition based on Ran-ASKS, independently maintained by
[pauliyyy](https://github.com/pauliyyy). It is not an official Ran-ASKS
distribution, Reference Distribution or compatibility certification.

- Repository: https://github.com/pauliyyy/Ran-Pauli-ASKS-windows
- Target branch: `Ran-Pauli-ASKS-Linux`.
- Baseline: pinned upstream 0.22.0 at the commit above; `VERSION` stays `0.22.0`.
- Purpose: complete upstream source with bounded Linux host/format/font adapters.
- Installation and operational limits: [operations/LINUX.md](operations/LINUX.md).
- Actual verification: [LINUX_VALIDATION.md](LINUX_VALIDATION.md).
- Linux changes: [LINUX_CHANGELOG.md](LINUX_CHANGELOG.md).

## Core modifications

| Paths | Linux responsibility |
| --- | --- |
| `.scripts/document_text.py`, `platform_compat.py` | Deterministic Word parsing, isolated bounded converters, host tool and font selection. |
| `.scripts/ingest_document.py`, `ingest_inbox.py` | Use the shared Word reader and native PPTX preview; preserve the existing ingestion, preview and failure contracts. |
| `.scripts/science_exhibit.py`, `science_exhibit_render.py`, `presentation_runtime.py` | Platform defaults and font-metric frame geometry with strict original render validation. |
| `.scripts/test_document_text.py`, `test_platform_compat.py`, `test_science_exhibit.py`, `test_suite.py` | Adapter/geometry regressions and ordered extension of the release profile. |
| `operations/engineering/graph.yaml`, `code-guidance.md`, public assets and manifest, Linux CI/docs | Shared boundary declaration, reproducible Linux setup, downstream publication and verification. |

The two backends retain the pinned upstream protocols and managed validators;
this edition does not add a semantic host or alter KU/Gallery policies. It does
not deploy or integrate the education system. Existing private state, secrets,
teacher knowledge and runtime environments are excluded from the public tree.
The upstream license and notices remain in force. Platform defects can be
proposed upstream separately under its contribution process; this PR updates
the independently maintained Linux branch only.
