本项目由离线隐私场景驱动，音频与文本默认不出本机；若需联网，请先在内网安全评审中通过。
# Offline Meeting Records

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
