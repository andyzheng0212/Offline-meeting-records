# Offline Meeting Records Web 绿色包

> **一句话价值主张：** 离线 · 本地 · 隐私优先的会议纪要与制度对照 Web 界面。

## 🎯 核心特性
- **快速版纪要**：多行要点一键转 Markdown，自动识别行动项。
- **录音校对**：上传 WAV 录音离线转写，生成校对摘要与差异报告。
- **制度对照**：导入 PDF/Word 制度库，全文检索匹配 Top-K 条款，提示仅供参考。
- **纪要导出**：根据模板导出 `.docx` 纪要，附行动项与制度提示。
- **一键销毁**：本地目录快速清理，可选集成 SDelete 覆盖删除。

## ⚙️ 绿色包使用步骤（Windows）
1. 在 GitHub Actions 的工件列表下载 `OfflineWebBundle_win.zip` 并解压到任意本地目录。
2. 将 Vosk 中文模型下载后解压到 `models/vosk-model-cn/`（目录须包含 `conf`、`am` 等子目录）。
3. 如需使用 SDelete 覆盖删除，请将 `sdelete64.exe` 放入 `bin/` 目录。
4. **双击 `start_web.bat`**（或右键“使用 PowerShell 运行” `start_web.ps1`）。
5. 首次运行脚本会自动创建 `.venv` 虚拟环境，并依次安装 `requirements.txt` 与 `requirements-web.txt`。
6. 浏览器访问 [http://localhost:8501](http://localhost:8501)，开始离线使用 Web UI。

> 若脚本提示找不到 Python，请安装 Python 3.10+ 并勾选“Add to PATH”。

## 🚀 首次冒烟测试流程
1. 在“快速版纪要”页输入 3 条要点，点击“生成快速版”，确认 `summaries/quick.md` 生成。
2. 在“录音转写校对”页上传一段 WAV 录音，执行转写并生成 `transcripts/trans_*.txt` 与 `summaries/sum_*.md`。
3. 在“政策导入与对照”页点击“导入政策库”（需在 `policy_source/` 放入 PDF/Word），确保提示导入条目数。
4. 在“政策导入与对照”页基于摘要触发检索，查看 Top-K 制度提示。
5. 在“导出纪要”页填写会议信息并导出 `.docx`，确认位于 `minutes/` 目录。
6. 在“一键销毁”页执行清理，检查 `audio_in/`、`transcripts/`、`summaries/`、`markers/` 目录被清空（`minutes/` 保留）。

## 📦 目录结构说明
```
OfflineWebBundle_win/
├─ app_web.py                # Streamlit Web 主程序
├─ README_WEB.md             # Web 使用说明（本文件）
├─ requirements.txt          # 桌面端共用依赖（随仓库更新）
├─ requirements-web.txt      # Web 端专用依赖（Streamlit + Watchdog）
├─ start_web.bat             # Windows 一键启动脚本
├─ start_web.ps1             # PowerShell 启动脚本
├─ config.yaml               # 全局配置（录音、ASR、目录、销毁策略）
├─ models/                   # Vosk / Whisper 等离线模型放置处（含 .gitkeep）
├─ bin/                      # 可选：放置 sdelete64.exe（含 .gitkeep）
├─ policy_db/                # SQLite 数据库存储位置（含 .gitkeep）
├─ policy_source/            # 待导入政策 PDF/Word（含 .gitkeep）
├─ audio_in/                 # 上传音频文件存放目录（含 .gitkeep）
├─ transcripts/              # 自动转写文本（含 .gitkeep）
├─ summaries/                # 快速版/校对摘要/差异报告（含 .gitkeep）
├─ minutes/                  # 导出的纪要 docx（含 .gitkeep）
└─ markers/                  # 重点标记 JSON（含 .gitkeep）
```

## 🛡️ 安全与隐私声明
- 全流程离线运行，无需联网；如需联网请先完成内网安全评审。
- “制度对照”功能仅作为提示，不构成任何合规结论或决策依据。
- “一键销毁”默认尝试使用 SDelete 覆盖删除；若未放置 `sdelete64.exe`，会自动降级为普通删除，并建议启用 BitLocker / VeraCrypt。
- 推荐将绿色包部署在全盘加密的设备上，定期导出成果后及时销毁音视频及临时文件。

## ❓ 常见问题 FAQ
- **录音没声怎么办？**
  - 上传的 WAV 文件需为 16kHz 单声道，可通过 `ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav` 重新采样。
  - 若仍无声，请在 `config.yaml` 的 `recording.device` 字段填写明确的设备名称或索引，或根据应用内弹出的“可用输入设备”列表逐项排查。
- **提示缺少 Vosk 模型？**
  - 确认 `models/vosk-model-cn/` 内含 `conf/`, `am/`, `rescore/` 等文件夹；目录名区分大小写。
  - 可访问 Vosk 官方镜像（离线下载后内网传输），再手动解压至该目录。
- **一键销毁失败？**
  - 检查 `bin/` 是否放置 `sdelete64.exe`；若缺失将使用普通删除，需额外依赖磁盘加密保证安全。
  - 若目录被其他程序占用，请关闭相关进程后重试。
- **政策对照没有结果？**
  - 确保 `policy_source/` 中已有内容充分的 PDF/Word 文档，并执行“导入政策库”。
  - 可尝试补充更多关键字或提高文档质量以提升匹配率。

## 🗂️ 版本与许可证
- 版本：v1.0.0（首次发布，后续请关注仓库 Changelog）
- 许可证：MIT License

