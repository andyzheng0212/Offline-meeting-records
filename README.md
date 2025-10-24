本项目由离线隐私场景驱动，音频与文本默认不出本机；若需联网，请先在内网安全评审中通过。
# Offline Meeting Records

## 🚀 项目价值主张
Offline Meeting Records 是一款面向政企本地部署的“离线、本地、隐私优先”会议纪要与制度对照助手。录音、识别、摘要、检索、导出及销毁全流程均在 Windows 终端完成，不依赖任何外网服务，帮助团队在内网环境快速形成合规纪要。 

## ✨ 核心功能
- 🎙️ **录音与锚点**：PySimpleGUI 界面一键录音，自动按 10 分钟切片，过程可随时标记重点并写入时间锚点。 
- ⚡ **快速纪要**：会中输入要点即可生成 Markdown 快速版，并自动抽取行动项。 
- 🛠️ **录音校对**：基于 Vosk 中文离线模型转写音频，自动生成校对摘要与差异报告。 
- ✅ **行动项抽取**：支持加载科室通讯录 CSV 作为人名词典，提高责任人识别准确度。 
- 📚 **制度对照**：导入 policy_source/ 下的 PDF / Word，构建 SQLite+FTS5 制度库，对纪要关键句检索并提示命中条款（仅提示，不构成合规结论）。 
- 🛡️ **一键销毁**：优先调用 SDelete 做覆盖删除，缺失时自动降级为普通删除并提示“建议开启 BitLocker/全盘加密”。 
- 🗂️ **多模板导出**：内置“通用 / 党委会 / 项目会 / 招采会”四套版式，Docx 一键导出。 

## 🧩 快速开始（Windows 绿色版）
1. 在 Release 或 Actions 工件中下载 `LocalMeetingBot_win` 压缩包并解压到本地。 
2. 下载 Vosk 中文模型（如 `vosk-model-small-cn-0.22`），解压至 `./models/vosk-model-cn/`。 
3. （可选）将科室通讯录导出为 CSV，放在 `./contacts/contacts.csv`。 
4. （可选）下载 [Sysinternals SDelete](https://learn.microsoft.com/sysinternals/downloads/sdelete)，复制 `sdelete64.exe` 至 `./bin/`。 
5. 双击 `LocalMeetingBot.exe` 即可启动，无需管理员权限或联网。 
6. 首次冒烟自检建议按照下列 6 步：
   1. 在“纪要撰写”输入 3 条要点，点击“生成快速版”，确认 `summaries/quick.md` 生成。 
   2. 执行“开始录音 → 标记重点 → 停止录音”，检查 `audio_in/` WAV 与 `markers/` JSON。 
   3. 点击“录音校对”，生成 `transcripts/trans_*.txt` 与 `summaries/sum_*.md`。 
   4. 在 `policy_source/` 放入两份 PDF/Word，执行“导入政策库”，确认提示条数。 
   5. 点击“政策对照”，查看匹配结果提示。 
   6. 填写会议信息并点击“导出纪要”，`minutes/` 生成 Docx 后，执行“一键销毁”验证清理提示。 

> 若使用源码运行：建议安装 Python 3.10～3.14，执行 `pip install -r requirements.txt`，然后 `python app.py`。
> 若使用源码运行：安装 Python 3.10+，执行 `pip install -r requirements.txt`，然后 `python app.py`。 

## ⚙️ 构建与自动化
- **本地打包**：
  ```powershell
  pyinstaller --noconfirm --clean --name LocalMeetingBot \
    --noconsole \
    --add-data "config.yaml;." \
    --add-data "models;models" \
    --add-data "policy_db;policy_db" \
    --add-data "bin;bin" \
    app.py
  ```
  打包后 dist/LocalMeetingBot/ 即为绿色版目录。 
- **GitHub Actions**：推送 `v*.*.*` 标签或手动 `workflow_dispatch` 会触发 `.github/workflows/windows-build.yml`，Windows runner 会安装依赖、执行上述 PyInstaller 命令，并上传 `LocalMeetingBot_win` 工件。
- **PyInstaller 配置亮点**：采用 PowerShell 参数数组防止续行解析错误；仅当目录存在时才附加 `--add-data`，避免空目录报错。
- **Web UI 绿色包**：推送 `v*.*.*` 标签或手动触发 `.github/workflows/windows-web-bundle.yml`，自动打包 `OfflineWebBundle_win.zip`，内含 Streamlit Web 程序、启动脚本与目录骨架，解压即可双击 `start_web.bat`。
- **GitHub Actions**：推送 `v*.*.*` 标签或手动 `workflow_dispatch` 会触发 `.github/workflows/windows-build.yml`，Windows runner 会安装依赖、执行上述 PyInstaller 命令，并上传 `LocalMeetingBot_win` 工件。 
- **PyInstaller 配置亮点**：采用 PowerShell 参数数组防止续行解析错误；仅当目录存在时才附加 `--add-data`，避免空目录报错。 

## 🔒 安全与隐私实践
- 默认全流程离线运行，无外部 API 调用。 
- `config.yaml` 可配置音频与转写保留天数（默认音频 0 天、转写 7 天）。 
- “一键销毁”优先使用 `bin/sdelete64.exe` 覆盖删除，缺失时自动回退普通删除并弹窗提示“建议开启 BitLocker/全盘加密”。 
- 支持自定义覆盖次数 `secure_delete.overwrite_passes`，同时保留 minutes/ 目录（可选勾选删除）。 
- 日志仅记录操作类型与时间，不记录正文。若需审计，可在 `logging.log_file` 配置路径。 
- **制度提示仅供参考，不构成合规结论，最终裁决请由合规部门确认。** 

## 📁 目录结构
## 项目简介
Offline Meeting Records 是一款专为 Windows 桌面场景打造的离线会议纪要助手，提供录音、快速纪要、录音校对、制度对照、纪要导出与敏感数据销毁的一站式流程。所有数据处理均在本地完成，不依赖云端服务，帮助团队满足隐私和合规要求。

### 核心特性
- **离线运行**：录音、语音识别、摘要、检索与导出全部在本机执行。
- **重点标记**：会议过程一键记录时间锚点，便于后续复盘。
- **快速纪要 & 校对**：会中快速输出纪要，会后结合录音自动校对并生成差异报告。
- **行动项智能抽取**：支持加载科室通讯录 CSV 作为人名词典，提升责任人识别准确度。
- **制度提示**：本地导入制度文件，全文检索关键句，仅提供提示不作裁决。
- **一键销毁**：支持调用 SDelete 覆盖删除，默认保留策略可配置。
- **多模板导出**：内置党委会、项目会、招采会三套纪要版式，可在导出时一键切换。
- **制度提示**：本地导入制度文件，全文检索关键句，仅提供提示不作裁决。
- **一键销毁**：支持调用 SDelete 覆盖删除，默认保留策略可配置。

## 环境准备
1. 安装 Python 3.10 及以上版本。
2. （推荐）在项目根目录创建虚拟环境：
   ```bash
   python -m venv .venv
   .venv\\Scripts\\activate
   ```
3. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
4. 下载 Vosk 中文模型（例如 `vosk-model-small-cn-0.22`），解压至 `./models/vosk-model-cn/`。
5. （可选）将科室通讯录导出为 CSV，放置在 `./contacts/contacts.csv`，并确保第一列或列名 `name` 为员工姓名。
6. （可选）下载并放置 `sdelete64.exe` 到 `./bin/`，用于覆盖删除。
5. （可选）下载并放置 `sdelete64.exe` 到 `./bin/`，用于覆盖删除。

## 运行方式
```bash
python app.py
```
启动后即可在 GUI 中完成录音、生成快速纪要、录音校对、制度检索与纪要导出；可在“制度与导出”页签选择纪要模板，并通过“查看行动项”实时确认抽取结果。
启动后即可在 GUI 中完成录音、生成快速纪要、录音校对、制度检索与纪要导出。

## PyInstaller 打包
使用以下命令生成独立可执行文件：
```bash
pyinstaller --name OfflineMeetingRecords \
  --onefile \
  --add-data "config.yaml;." \
  --add-data "policy_source;policy_source" \
  --add-data "models;models" \
  app.py
```
> 根据实际模型体积，建议在打包后手工确认模型目录是否正确拷贝。

## GitHub Actions 自动构建
- 工作流文件位于 `.github/workflows/windows-build.yml`。
- Push 或手动触发（workflow_dispatch）携带 `v*.*.*` 标签即可启动构建。
- 构建流程：安装依赖 → PyInstaller 打包 → 上传 `dist/OfflineMeetingRecords/` 目录为工件。
- 在 GitHub Actions 页面下载 Artifacts 即可获取打包结果。

## 目录说明
```
Offline-meeting-records/
├─ app.py                  # GUI 主程序
├─ recorder.py             # 录音与时间锚点
├─ asr_vosk.py             # Vosk/Faster-Whisper 构建入口
├─ summarizer.py           # 摘要、行动项、差异报告
├─ policy_db.py            # 制度库导入与全文检索
├─ formatter_docx.py       # 纪要 Docx 导出
├─ destroyer.py            # SDelete/普通删除
├─ config.yaml             # 默认配置（Vosk 引擎）
├─ requirements.txt        # CPU 方案依赖
├─ advanced/               # 高精度可选组件（faster-whisper）
│  ├─ asr_fwhisper.py
│  ├─ config-advanced.yaml
│  └─ requirements-advanced.txt
├─ models/                 # 放 Vosk 或 whisper 模型（含 .gitkeep）
├─ bin/                    # 放 sdelete64.exe（含 .gitkeep）
├─ policy_source/          # 制度原文目录
├─ policy_db/              # SQLite 数据库目录
├─ audio_in/               # 录音切片输出
├─ markers/                # 重点标记 JSON
├─ transcripts/            # 转写文本
├─ summaries/              # 摘要与差异报告
├─ minutes/                # 导出的 Docx
├─ .github/workflows/windows-build.yml
├─ README.md / LICENSE / .gitignore
└─ .gitkeep                # 空目录占位
```
`.gitignore` 已排除模型、音频、转写、制度库、可执行文件等敏感或体积较大文件。 

## ❓ FAQ
- **录音无声或设备不可用怎么办？**
  - 启动时若配置的设备无效，程序会列出可用设备并自动回退到系统默认。可在 `config.yaml` 中填写 `recording.device` 索引。
  - 请确认麦克风权限已开启，必要时在“声音设置”中启用输入设备。
- **录音没声怎么办？**
  - 打开 `config.yaml`，将 `recording.device` 写成固定的设备索引或名称，避免系统自动切换错误设备。
  - 参照窗口弹出的“可用输入设备”列表，选取正确麦克风后填入配置，或逐一测试列表中的备选项。
- **语音识别速度慢？**
  - 选择更轻量的 Vosk 模型，或切换至 Advanced faster-whisper（需更高算力）。
  - 确保音频采样率为 16kHz 单声道。
  - 启动时若配置的设备无效，程序会列出可用设备并自动回退到系统默认。可在 `config.yaml` 中填写 `recording.device` 索引。 
  - 请确认麦克风权限已开启，必要时在“声音设置”中启用输入设备。 
- **语音识别速度慢？**
  - 选择更轻量的 Vosk 模型，或切换至 Advanced faster-whisper（需更高算力）。 
  - 确保音频采样率为 16kHz 单声道。 
- **行动项责任人识别错误？**
  - 在 `contacts/contacts.csv` 准备人员名单（首列或 name 列为姓名），应用将优先匹配词典。 
- **政策库未命中？**
  - 确认 `policy_source/` 中存在 PDF/Word 文件，导入时若为空会弹窗提示并跳过。 
  - 检查关键词是否覆盖政策原文中的表述。 
- **销毁无效或提示降级？**
  - `bin/sdelete64.exe` 缺失会自动改为普通删除，并弹窗提醒“建议开启全盘加密”。 
  - 若需强制覆盖删除，请确保以管理员身份运行并确认磁盘权限。 

## 🌟 Advanced：更高精度的离线识别（可选安装）
- 适用场景：需要更高准确率且具备较强 CPU/GPU 资源。 
- 使用步骤：
  1. 安装依赖：`pip install -r advanced/requirements-advanced.txt`。 
  2. 下载并解压 faster-whisper 模型至 `models/faster-whisper-large-v2/`（可替换为合适体积）。 
  3. 选择其一：
     - 将 `advanced/config-advanced.yaml` 覆盖根目录 `config.yaml`；或
     - 手动在现有 `config.yaml` 中将 `asr.engine` 改为 `faster-whisper`，并按需设置 `compute_type/beam_size`。 
  4. 重新启动应用，状态栏将显示 ASR 已就绪。 
- Advanced 方案不改变主线流程，随时可切回默认 Vosk 配置。 

## 🗒️ 版本与 Changelog
- 当前版本：v1.0.0（初始化离线流程 + UI 成品版）。 
- Changelog：
  - v1.0.0：首次发布，完成录音 → 快速版 → 校对 → 制度对照 → 导出 → 销毁全流程。 
  - （占位）后续更新将在此处记录。 

## 📄 许可证
本项目以 [MIT License](LICENSE) 发布，可在保持离线与隐私前提下自由使用与二次开发。 

├─ asr_vosk.py             # Vosk 离线识别
├─ summarizer.py           # 摘要、行动项、差异报告
├─ policy_db.py            # 制度库导入与全文检索
├─ formatter_docx.py       # 纪要 Docx 导出
├─ destroyer.py            # 一键销毁
├─ config.yaml             # 配置文件
├─ requirements.txt        # 依赖
├─ README.md               # 文档
├─ LICENSE                 # MIT 许可
├─ .gitignore              # 忽略规则
├─ .github/workflows/windows-build.yml  # CI 工作流
├─ models/                 # Vosk 模型目录（默认忽略）
├─ bin/                    # SDelete 可执行目录（默认忽略）
├─ audio_in/               # 录音输出（运行时生成）
├─ markers/                # 标记文件（运行时生成）
├─ transcripts/            # 转写文本
├─ summaries/              # 摘要与差异报告
├─ minutes/                # 纪要导出
├─ policy_source/          # 制度原文件
├─ policy_db/              # SQLite 数据库
└─ contacts/               # 科室通讯录（CSV，默认忽略）
└─ policy_db/              # SQLite 数据库
```

`.gitignore` 默认排除模型、音频、转写、摘要、制度库、可执行文件等敏感或体积较大的内容，避免误提交。

## 隐私与安全注意事项
- 建议启用 BitLocker 或其他磁盘加密，避免设备遗失造成数据泄露。
- `config.yaml` 中可配置音频、转写保留天数，默认音频纪要生成后立即删除、转写保留 7 天。
- 日志仅记录操作类型与时间，未写入正文；如需审计，可在配置中指定日志文件路径。
- 制度提示仅供参考，不构成合规结论，最终裁决请由合规部门确认。

## FAQ
**Q: 录音无声或设备不可用怎么办？**  
A: 在 `config.yaml` 中设置 `recording.device` 为正确的设备索引，或检查麦克风权限。

**Q: 语音识别速度慢？**  
A: 更换体积更小的 Vosk 模型或提升本地 CPU 性能，确保音频采样率为 16kHz 单声道。

**Q: 一键销毁提示失败？**
A: 检查 `bin/sdelete64.exe` 是否存在以及权限是否足够；若缺失将自动回退到普通删除。

**Q: 政策库无匹配结果？**
A: 确认 `policy_source/` 已放置 PDF/Word 文件并重新执行“导入政策库”，同时检查检索关键词是否准确。

**Q: 行动项责任人识别错误？**
A: 请准备通讯录 CSV（支持含表头的 `name` 列或无表头第一列），更新 `config.yaml` 的 `summary.contact_csv` 路径并重启应用。

**Q: 一键销毁提示失败？**  
A: 检查 `bin/sdelete64.exe` 是否存在以及权限是否足够；若缺失将自动回退到普通删除。

**Q: 政策库无匹配结果？**  
A: 确认 `policy_source/` 已放置 PDF/Word 文件并重新执行“导入政策库”，同时检查检索关键词是否准确。

## CI 与打包自检
- `pip install -r requirements.txt` 正常。
- `python app.py` 可启动 GUI。
- GUI 中依次执行“生成快速版”“录音校对”“政策对照”“导出纪要”“一键销毁”流程，文件生成与销毁均符合预期。
