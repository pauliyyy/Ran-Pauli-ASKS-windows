# Ubuntu 安装、运行与验证

本页是 Ran-ASKS 在 Ubuntu 上的宿主环境契约。平台适配只替换命令发现、文档
转换、桌面打开和可恢复清理的宿主接口；Raw、Wiki、Graph、Agent/API、分类、
语义、校验和事务行为不因 Ubuntu 版本而改变。

## 支持基线

- Ubuntu 22.04 及其后续版本；版本判断以运行能力而不是发行版名称硬编码。
- Python 3.10 或更高版本。Ubuntu 22.04、24.04、26.04 的默认 Python 分别落在
  本项目的 3.10+ 语法基线内。
- 仓库路径必须位于 Linux 文件系统或提供完整 POSIX 文件语义的挂载点；脚本不依赖
  macOS 大小写不敏感文件系统。
- 桌面程序、远程模型和可选提取后端可以缺席；对应工作流必须明确报告缺少的工具，
  不能把未执行伪装为成功。

更老的 Ubuntu 只有在另行提供 Python 3.10+ 和下列同名系统工具时才属于支持范围。
不要为了兼容旧解释器改写或删除知识库能力。

## 安装

先安装 Python 虚拟环境和已有功能使用的系统工具：

```bash
sudo apt-get update
sudo apt-get install -y \
  python3 python3-venv python3-pip git curl ripgrep \
  libreoffice \
  tesseract-ocr tesseract-ocr-eng tesseract-ocr-chi-sim \
  fonts-noto-cjk xdg-utils libglib2.0-bin
```

`ripgrep` 服务受管 IP 重定位的引用完整性扫描；`libreoffice` 提供 PPT/PPTX 静态
渲染和旧 `.doc` 转换；PPTX 分类预览复用项目的原生 OOXML 提取器，不依赖 Pandoc；
Tesseract 只服务已有的可编辑 PPT 重建 OCR；Noto CJK 字体降低不同 Ubuntu 版本间
的中文换行差异；`xdg-open`、`gio` 分别提供桌面打开和 Freedesktop 回收站接口。
无桌面的服务器仍可生成文件，`--open` 只会给出提示，不影响生成结果。

在仓库根目录创建隔离环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 .scripts/ubuntu_preflight.py --python-only --strict
cp .env.example .env
```

`requirements.txt` 包含共享运行时和仓库回归所需 Python 包。只有显式选择本地
Docling 后端时才创建脚本约定的独立环境：

```bash
python3 -m venv .venv-docling
.venv-docling/bin/python -m pip install --upgrade pip
.venv-docling/bin/python -m pip install \
  torch torchvision --index-url https://download.pytorch.org/whl/cpu
.venv-docling/bin/python -m pip install -r requirements-docling.txt
python3 .scripts/ubuntu_preflight.py --docling --strict
```

上面的 PyTorch CPU 索引适合默认的无 GPU Ubuntu 服务器，并避免从 PyPI
额外安装 CUDA 运行时。确需 NVIDIA GPU 时，按 PyTorch 官方安装矩阵替换该行，
再安装 `requirements-docling.txt`；不要在同一环境混装 CPU 与 CUDA wheel。

需要远程模型的工作流再配置 `.env`；本地结构校验不需要 API key。

## 平台行为

| 能力 | Ubuntu 适配 | 缺少工具时的行为 |
| --- | --- | --- |
| `.docx` 正文 | 标准库按 Transitional/Strict OOXML 结构读取正文、嵌套内容、表格及实际引用的页眉页脚、脚注和尾注 | 非法或损坏文件返回空提取，由既有摄入校验阻断 |
| 旧 `.doc` 正文 | 优先 LibreOffice；也兼容 `antiword` / `catdoc` | 返回空提取，由既有摄入校验阻断，不生成伪正文 |
| PPT/PPTX 静态页 | 从 `SOFFICE_BIN`、PATH 或标准安装位置发现 LibreOffice | 明确报告需要 `soffice`，不降格为视觉通过 |
| `graph_visualize.py --open` | 原生 Ubuntu 使用 `xdg-open`，其次 `gio open`；WSL 将 Linux 路径转换为 Windows 路径，并兼容窗口已创建但 opener 返回非零的行为 | 文件仍生成，只提示手动打开 |
| 摄入后的可恢复清理 | `gio trash`，其次 `trash-put` / `trash` | 移到仓库 `temp/trash/`，绝不永久删除 |
| 图片/PDF/PPT 视觉检查 | PyMuPDF/Pillow + 可选 LibreOffice | 缺依赖或渲染器时明确失败/partial |

调用方设置的 `FONTCONFIG_FILE` / `FONTCONFIG_PATH` 始终优先。适配层不安装字体、
不修改全局环境，也不修改来源文件。

## 验证

在激活 `.venv` 后，先对部署机执行严格宿主验收：

```bash
python3 .scripts/ubuntu_preflight.py --strict --smoke
```

该命令实际导入 Python 依赖，并检查 `git`、`curl`、`rg`、Tesseract 及 `eng`/`chi_sim`
语言、LibreOffice、桌面打开器和系统回收站，并在系统临时目录实际完成一次
PPTX → PDF 转换及文本核对。任何 missing/failed 都以非零状态退出；不带
`--strict` 时只生成安装诊断，不代表部署验收通过。无桌面服务器仍需有 opener
命令，但不会真的拉起桌面应用。

WSL 桌面验收应另用一个已存在的临时目录实际执行 `--open`，并确认只出现一个
带该目录标题和非零窗口句柄的 Explorer 窗口；命令存在性检查不能替代这一步。

宿主验收通过后运行代码回归：

```bash
python3 .scripts/test_platform_compat.py
python3 .scripts/test_ingest_document.py
python3 .scripts/test_ingest_inbox_dispatch.py
python3 .scripts/test_visual_qa.py
python3 dsh/test_visual_tools.py
python3 .scripts/test_prompt_audit.py
python3 .scripts/engineering_graph.py validate
```

`test_platform_compat.py` 使用受控假命令检查失败与回退分支，不能替代上面的真实
宿主验收。平台 smoke 使用自动清理的系统临时目录；两者均不写 Raw、Wiki 或
`graph.db`。图校验继续经受管 Python 入口执行；不得用不存在的路径启动裸
`sqlite3`。
