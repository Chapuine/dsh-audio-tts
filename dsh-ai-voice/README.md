# dsh-ai-voice

DSH（DeepSeek Harness）AI 智能配音插件。**先识别音色 → AI 自动调参 → 合成语音输出**，全程复用 dsh 当前模型做决策，TTS 引擎使用免费的 edge-tts，无需任何 API Key。

## 功能特性

- **音色识别**：分析参考音频，自动提取性别、年龄感、语速、音量、音色亮度、情感风格
- **AI 自动调参**：DeepSeek 模型根据音色画像 + 文本语境，自动选择最合适的 TTS 参数
- **多音色支持**：内置 20+ 中文 Neural 音色（温暖女声、播音男声、童声、磁性低音等）
- **参数精细调节**：语速、音调、音量均可微调
- **长文本处理**：自动分句合成后拼接，支持数千字文稿
- **完全免费**：基于 edge-tts（微软 Edge 在线 TTS），无需注册、无需 API Key

## 目录结构

```
dsh-ai-voice/
├── SKILL.md                       # Skill 定义：三段式工作流与参数决策规则
├── README.md                      # 本文件
└── scripts/
    ├── analyze_voice.py           # 音色识别脚本（librosa）
    └── generate_voice.py          # TTS 合成脚本（edge-tts）
```

## 安装

### 1. 安装依赖

```bash
pip install edge-tts librosa numpy soundfile
```

### 2. 安装到 dsh skills 目录

把 `dsh-ai-voice` 文件夹放入 dsh 的 skills 目录：

```bash
cp -r dsh-ai-voice ~/.dsh/skills/
```

重启 dsh 即可生效。

## 使用

对 dsh 说类似的话即可触发：

- "帮我把这段文字配个音"
- "用这个音频的音色帮我念这段稿子"
- "生成一个温柔女声的有声书旁白"
- "做一个广告配音，要激昂一点"

### 脚本单独使用

**音色识别：**

```bash
python3 scripts/analyze_voice.py /path/to/reference.mp3 --output profile.json
```

**TTS 合成：**

```bash
# 基础用法
python3 scripts/generate_voice.py --text "你好，世界" --out hello.mp3

# 指定音色和参数
python3 scripts/generate_voice.py \
    --text "这是一段广告文案" \
    --voice zh-CN-XiaochenNeural \
    --rate "+15%" \
    --pitch "+8Hz" \
    --volume "+10%" \
    --out ad.mp3

# 从文件读取长文本
python3 scripts/generate_voice.py --file script.txt --voice zh-CN-YunxiNeural --out narration.mp3

# 列出所有可用中文音色
python3 scripts/generate_voice.py --list-voices
```

## 常用中文音色参考

| 音色 ID | 风格 |
| --- | --- |
| `zh-CN-XiaoxiaoNeural` | 晓晓：温暖女声，通用首选 |
| `zh-CN-XiaoyiNeural` | 晓伊：自然清爽女声 |
| `zh-CN-XiaochenNeural` | 晓辰：明亮活泼，广告促销 |
| `zh-CN-XiaoqiuNeural` | 晓秋：知性专业，课程讲座 |
| `zh-CN-XiaoyouNeural` | 晓悠：柔和舒缓，助眠冥想 |
| `zh-CN-XiaoshuangNeural` | 晓双：童声，儿童故事 |
| `zh-CN-YunxiNeural` | 云希：青年男声，最常用 |
| `zh-CN-YunyangNeural` | 云扬：播音腔，新闻播报 |
| `zh-CN-YunjianNeural` | 云健：低沉成熟，广告纪录片 |
| `zh-CN-YunfengNeural` | 云枫：稳重正式，企业宣传片 |
| `zh-CN-YunyeNeural` | 云野：磁性深情，情感电台 |

## 依赖

- Python 3.8+
- edge-tts（TTS 合成）
- librosa + numpy（音色识别）
- soundfile（音频读写）

## 注意事项

- 需要网络连接（edge-tts 为在线服务）
- 参考音频建议：清晰人声、无强背景音乐、时长 ≥ 2 秒
- 单次合成建议不超过 2000 字，超长自动分句拼接
