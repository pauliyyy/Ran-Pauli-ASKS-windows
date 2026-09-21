# Third-party Projects and Engineering Influences

This document records material upstream projects used by or consulted during
the development of Ran-ASKS. It distinguishes runtime dependencies from
optional backends, architectural influences, and projects that are not part of
the current implementation.

The relationship labels mean:

- **Runtime dependency**: Ran-ASKS imports or calls the project in the named
  workflow. The dependency is not vendored in this repository unless stated.
- **Regression dependency**: the project is used to construct or verify test
  fixtures and is installed by the shared regression environment.
- **Optional backend**: the project is used only when that backend is explicitly
  configured or selected.
- **Architectural influence**: Ran-ASKS adopted named design ideas and
  implemented them independently in its own architecture.
- **Adapted pattern**: Ran-ASKS translated a specific upstream pattern into its
  own data model or execution contract without importing the upstream runtime.
- **Not integrated**: the project informed evaluation or future planning but is
  not part of the released system.

## Material upstream projects

| Project | Relationship | Scope in Ran-ASKS | Upstream terms recorded by this project |
| --- | --- | --- | --- |
| [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) | Architectural influence | The optional `dsh/` cockpit adapts the ToolRegistry, hook cascade, in-memory session log, guard chain, and plugin-oriented design as a Python implementation. Ran-ASKS does not depend on the upstream runtime. | MIT |
| [Semantica](https://github.com/semantica-agi/semantica) | Adapted pattern | Declarative graph constraints, provenance records, and temporal-validity patterns informed the graph-governance layer. Ran-ASKS retains its own single graph store and Raw evidence boundary and does not import an RDF/OWL runtime. | MIT |
| [MinerU](https://github.com/opendatalab/MinerU) | Preferred external extraction backend | Structured PDF extraction for paper ingestion. Ran-ASKS consumes configured service output and does not vendor MinerU source. | MinerU Open Source License; service terms may also apply |
| [Docling](https://github.com/docling-project/docling) | Optional local backend | Local document extraction when explicitly selected. Paper ingestion does not silently fall back to Docling. | MIT |
| [PyMuPDF](https://github.com/pymupdf/PyMuPDF) | Runtime dependency for PDF and visual workflows | PDF text-layer access, page rendering, metadata extraction, and vector-object inspection in ingestion, visual QA, and editable-PPT reconstruction. The package is not vendored here. | AGPL-3.0 or a separate commercial license from its vendor |
| [python-pptx](https://github.com/scanny/python-pptx) | Runtime dependency for slide workflows | Creation of native PowerPoint text boxes, lines, shapes, freeforms, and related Open XML objects. | MIT |
| [PyYAML](https://github.com/yaml/pyyaml) | Runtime dependency | Parsing the YAML schemas, configuration, and engineering graph. | MIT |
| [NumPy](https://numpy.org/) | Runtime dependency | Embedding math, graph semantics, clustering, and editable-PPT image analysis. | BSD-3-Clause; binary distributions may include separately licensed components |
| [SciPy](https://scipy.org/) | Runtime dependency | Hierarchical clustering, spatial distances, and image morphology. | BSD-3-Clause; binary distributions may include separately licensed components |
| [Matplotlib](https://matplotlib.org/) | Runtime dependency | Static graph visualization. | Matplotlib License (PSF-compatible) |
| [NetworkX](https://networkx.org/) | Runtime dependency | Graph layout and visualization preparation. | BSD-3-Clause |
| [rank-bm25](https://github.com/dorianbrown/rank_bm25) | Runtime dependency | BM25 baseline navigation and evaluation. | Apache-2.0 |
| [tiktoken](https://github.com/openai/tiktoken) | Runtime dependency | Token accounting for baseline navigation. | MIT |
| [Requests](https://requests.readthedocs.io/) | Runtime dependency | HTTP transport for the configured MinerU extraction service. | Apache-2.0 |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | Runtime dependency | Optional `.env` loading for extraction configuration. | BSD-3-Clause |
| [Pillow](https://python-pillow.org/) | Runtime dependency | Image normalization, diagnostics, OCR preparation, and editable-PPT reconstruction. | MIT-CMU |
| [openpyxl](https://openpyxl.readthedocs.io/) | Runtime dependency | Faithful `.xlsx` extraction, including formula and worksheet metadata. | MIT |
| [xlrd](https://github.com/python-excel/xlrd) | Runtime dependency | Faithful legacy `.xls` extraction. | BSD |
| [xlwt](https://github.com/python-excel/xlwt) | Regression dependency | Construction of legacy `.xls` extraction fixtures. | BSD |
| [SQLite](https://www.sqlite.org/) | Standard-library storage backend | The Python `sqlite3` interface provides the single-file graph database used by Ran-ASKS. | Public domain |

## Related projects not integrated

| Project | Relationship | Current boundary |
| --- | --- | --- |
| [Cordis](https://github.com/cordiverse/cordis) | Architectural context | The original TypeScript runtime was reviewed in relation to DSH. It is not a Ran-ASKS dependency; the released cockpit is implemented in Python. |
| [Leiden](https://github.com/vtraag/leidenalg) | Future-method reference | Community detection was considered for future knowledge-structure analysis. It is not used by the current released system. |

## License boundary

Ran-ASKS is distributed under the license in [LICENSE](LICENSE). That license
applies to Ran-ASKS code and documentation; it does not replace the terms of
third-party projects, packages, model endpoints, or external services.

In particular, PyMuPDF is recorded as AGPL-3.0 with a commercial-license option.
Users who enable workflows that depend on PyMuPDF should evaluate the applicable
upstream terms for their distribution and deployment model. Commercial use of
Ran-ASKS and commercial rights for a third-party dependency are separate
questions.

No source code from an architectural-influence project is claimed as original
Ran-ASKS code. Where future development copies or adapts upstream code rather
than design ideas, the corresponding file-level notice and license obligations
must be recorded before release.

Upstream projects and licenses can change. The linked upstream repositories are
the authoritative sources for their current terms.
