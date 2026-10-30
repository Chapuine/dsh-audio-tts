---
name: dsh-ai-voice
description: AI 智能配音插件。先分析用户提供的参考音频识别音色特征（性别、年龄、语速、情感风格），再由当前 DeepSeek 模型根据音色画像和待配音文本内容自动调整 TTS 参数（音色选择、语速、音调、音量），最后调用 edge-tts 生成自然语音输出 MP3。适用于用户需要将文本转为语音、配音、有声书、视频旁白、广告配音、课件讲解、角色配音等场景；当用户说"配音""朗读""生成语音""TTS""AI 配音""念出来""声音输出"或提供参考音频要求模仿音色时触发。
---

# dsh-ai-voice

## 概述

三段式 AI 配音流水线：

1. **音色识别** — 分析用户提供的参考音频，提取基频、语速、能量、频谱等声学特征，输出结构化音色画像 JSON。
2. **AI 自动调参** — 当前 DeepSeek 模型阅读音色画像 + 待配音文本的语境（情感、场景、风格），自动决策最终 TTS 参数（voice / rate / pitch / volume）。
3. **语音合成输出** — 用决策好的参数调用 edge-tts 生成 MP3 音频文件。

不引入付费 API，复用 edge-tts 免费接口。全程不离开 dsh 环境。

## 工作流

### 第 1 步：收集输入

向用户确认两样输入（缺哪样补哪样）：

- **待配音文本**：要朗读的文字内容（直接粘贴或给文件路径）。
- **参考音频**（可选）：用户希望模仿的音色样本。
  - 本地路径：直接使用。
  - URL：先下载到临时目录再分析。
  - 用户没给参考音频：跳过音色识别，直接根据文本内容选择默认音色并走第 3 步。

### 第 2 步：音色识别（有参考音频时）

运行分析脚本：

```bash
python3 <SKILL_ROOT>/scripts/analyze_voice.py <参考音频路径> --output <输出目录>/voice_profile.json
```

其中 `<SKILL_ROOT>` 为本 skill 所在目录（含 SKILL.md 的目录）。

脚本输出 JSON 包含：

- `voice_profile.gender` — 推断性别（male / female / unknown）
- `voice_profile.age_hint` — 年龄感描述
- `voice_profile.f0_hz` — 基频统计
- `voice_profile.speaking_rate` — 语速等级与每秒音节数
- `voice_profile.volume` — 音量等级
- `voice_profile.timbre` — 音色明亮度（warm / neutral / bright）
- `voice_profile.emotion_style` — 情感风格（calm / moderate / expressive）
- `tts_suggestion` — 脚本自动给出的初始 TTS 参数建议

### 第 3 步：AI 自动调参（核心决策）

**你（DeepSeek 模型）必须在这一步做参数决策**，不要直接照抄脚本的 `tts_suggestion`，要结合：

1. **音色画像**（第 2 步输出）：尽量贴近参考音频的性别、语速、音色亮度。
2. **待配音文本的语境**：判断文本类型和情感，反向修正参数。
3. **用户的显式要求**：如"要激昂一点""慢一点""温柔一点"。

#### 参数决策规则

**音色选择（voice）**：优先从以下中文 Neural 音色中选，与参考音频性别一致：

| 性别 | 文本风格 | 推荐 voice |
| --- | --- | --- |
| 女 | 温暖/情感/日常/故事 | `zh-CN-XiaoxiaoNeural` |
| 女 | 资讯/讲解/课程 | `zh-CN-XiaoqiuNeural` |
| 女 | 广告/促销/活泼 | `zh-CN-XiaochenNeural` |
| 女 | 温柔/治愈/助眠 | `zh-CN-XiaoyouNeural` |
| 女 | 童声/儿童故事 | `zh-CN-XiaoshuangNeural` |
| 男 | 通用/青年/日常 | `zh-CN-YunxiNeural` |
| 男 | 新闻/播报/正式 | `zh-CN-YunyangNeural` |
| 男 | 低沉/广告/纪录片 | `zh-CN-YunjianNeural` |
| 男 | 沉稳/企业/正式 | `zh-CN-YunfengNeural` |
| 男 | 磁性/情感/深夜电台 | `zh-CN-YunyeNeural` |

完整音色列表：`python3 <SKILL_ROOT>/scripts/generate_voice.py --list-voices`

**语速（rate）**：
- 参考音频语速 → 脚本已给初始 `edge_rate_hint`
- 正式播报/新闻 → `+0%` 到 `+5%`
- 情感/故事/散文 → `-5%` 到 `+0%`
- 广告/促销/激情 → `+10%` 到 `+20%`
- 儿童/温柔/助眠 → `-15%` 到 `-5%`

**音调（pitch）**：
- 脚本已根据 F0 偏移给出 `pitch_hz` 建议（±50Hz 以内）
- 激昂/兴奋 → 在建议基础上再 `+5~10Hz`
- 低沉/严肃 → 在建议基础上再 `-5~10Hz`
- 中性叙述 → 用建议值

**音量（volume）**：默认 `+0%`；旁白/视频配音可 `+10%` 提高可懂度。

#### 调参决策输出格式

在生成音频前，先用一段简短文字告诉用户你选了什么参数、为什么：

> 音色识别结果：女性青年、语速偏快、音色明亮、情感丰富。
> 结合这段广告文案需要活力感，我选择：
> - 音色：晓辰（`zh-CN-XiaochenNeural`）— 明亮活泼女声
> - 语速：`+15%` — 广告节奏
> - 音调：`+8Hz` — 提升活力感
> - 音量：`+10%` — 保证穿透力

### 第 4 步：语音合成

运行合成脚本：

```bash
python3 <SKILL_ROOT>/scripts/generate_voice.py \
    --text "<待配音文本>" \
    --out <输出目录>/output.mp3 \
    --voice <选定的voice> \
    --rate "<rate>" \
    --pitch "<pitch>" \
    --volume "<volume>"
```

长文本可以写到临时 `.txt` 文件后用 `--file <路径>` 传入，避免命令行转义问题。

脚本会自动：
- 按句子切分长文本（每段 ~300 字）后拼接
- 输出 MP3 文件路径和文件大小

### 第 5 步：交付

- 用文件交付方式把生成的 MP3 给用户。
- 告知用户文件路径、使用的参数、音色名称。
- 如果用户对结果不满意，根据反馈微调参数（语速、音调、音色）后重新生成。

## 注意事项

- 本 skill 依赖 edge-tts 在线服务，需要网络连接；离线环境下明确告知用户。
- 首次使用需安装依赖：`pip install edge-tts librosa numpy soundfile`。
- 参考音频要求：清晰人声、无强背景音乐、时长 ≥ 2 秒；否则分析结果不可靠。
- 合成文本支持中文、英文、中英混排；数字和标点 edge-tts 会自动处理。
- 单次合成文本建议不超过 2000 字；超长文本脚本会自动分句拼接。
- 不要编造不存在的音色名；所有 voice 必须来自 `--list-voices` 输出或本文件列出的音色。
- 如果用户明确指定了音色/风格，优先遵循用户要求，不要强行用参考音频覆盖。
