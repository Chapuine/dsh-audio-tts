# dsh-audio-tts

DSH（DeepSeek Harness）AI 智能配音插件。**先识别音色 → AI 自动调参 → 合成语音输出**，全程复用 dsh 当前模型做决策，TTS 引擎使用免费的 edge-tts，无需任何 API Key。

## 功能特性

- **音色识别**：分析参考音频，自动提取性别、年龄感、语速、音量、音色亮度、情感风格
- **AI 自动调参**：DeepSeek 模型根据音色画像 + 文本语境，自动选择最合适的 TTS 参数
- **多音色支持**：内置 20+ 中文 Neural 音色（温暖女声、播音男声、童声、磁性低音等）
- **参数精细调节**：语速、音调、音量均可微调
- **长文本处理**：自动分句合成后拼接，支持数千字文稿
- **完全免费**：基于 edge-tts（微软 Edge 在线 TTS），无需注册、无需 API Key

## 工作流

```
参考音频（可选）
     │
     ▼
┌─────────────────┐
│  analyze_voice   │  提取 F0 / 语速 / 能量 / 频谱
│  .py            │  输出结构化音色画像 JSON
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  DeepSeek 模型   │  阅读音色画像 + 文本语境
│  AI 自动调参     │  决策 voice / rate / pitch / volume
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  generate_voice │  调用 edge-tts
│  .py            │  输出 MP3 音频文件
└─────────────────┘
```

## 目录结构

```
dsh-audio-tts/
├── dsh-ai-voice/               # 插件目录
│   ├── SKILL.md                # Skill 定义：三段式工作流与参数决策规则
│   ├── README.md               # 插件说明
│   └── scripts/
│       ├── analyze_voice.py    # 音色识别脚本（librosa）
│       └── generate_voice.py   # TTS 合成脚本（edge-tts）
└── README.md                   # 本文件
```

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/Chapuine/dsh-audio-tts.git
```

### 2. 安装依赖

```bash
pip install edge-tts librosa numpy soundfile
```

### 3. 安装到 dsh skills 目录

把 `dsh-ai-voice` 文件夹放入 dsh 的 skills 目录：

```bash
cp -r dsh-audio-tts/dsh-ai-voice ~/.dsh/skills/
```

重启 dsh 即可生效。

## 使用

对 dsh 说类似的话即可触发：

- "帮我把这段文字配个音"
- "用这个音频的音色帮我念这段稿子"
- "生成一个温柔女声的有声书旁白"
- "做一个广告配音，要激昂一点"

## 依赖

- Python 3.8+
- edge-tts（TTS 合成）
- librosa + numpy（音色识别）
- soundfile（音频读写）

## License

MIT
