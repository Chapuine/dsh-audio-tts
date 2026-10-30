#!/usr/bin/env python3
"""dsh-ai-voice TTS 语音合成脚本。

基于 edge-tts（微软 Edge 在线 TTS 接口，免费、无需 API Key），
将文本合成为自然语音，支持：
- 多音色选择（中文 Neural 音色）
- 语速 / 音调 / 音量微调
- 长文本自动分句合成后拼接
- 输出 MP3 文件

用法：
    python3 generate_voice.py --text "你好世界" --out output.mp3
    python3 generate_voice.py --file script.txt --voice zh-CN-YunxiNeural \\
        --rate "+10%" --pitch "+5Hz" --out demo.mp3
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile


# 常用中文音色表，供 agent 参考选择
ZH_VOICES = {
    # 女声
    "zh-CN-XiaoxiaoNeural":   "晓晓 - 温暖女声（通用，适合情感/日常）",
    "zh-CN-XiaoyiNeural":     "晓伊 - 自然女声（清爽，适合资讯/讲解）",
    "zh-CN-XiaochenNeural":   "晓辰 - 明亮女声（活泼，适合广告/促销）",
    "zh-CN-XiaohanNeural":    "晓涵 - 温柔女声（知性，适合电台/散文）",
    "zh-CN-XiaomengNeural":   "晓梦 - 甜美女声（可爱，适合儿童/萌系）",
    "zh-CN-XiaomoNeural":     "晓墨 - 沉稳女声（成熟，适合纪录片）",
    "zh-CN-XiaoqiuNeural":    "晓秋 - 知性女声（专业，适合课程/讲座）",
    "zh-CN-XiaoruiNeural":    "晓睿 - 干练女声（商务，适合播报）",
    "zh-CN-XiaoshuangNeural": "晓双 - 童声（适合儿童故事）",
    "zh-CN-XiaoxuanNeural":   "晓萱 - 活力女声（热情，适合直播）",
    "zh-CN-XiaoyanNeural":    "晓颜 - 亲切女声（温暖，适合客服）",
    "zh-CN-XiaoyouNeural":    "晓悠 - 柔和女声（舒缓，助眠/冥想）",
    # 男声
    "zh-CN-YunxiNeural":      "云希 - 青年男声（通用，最常用）",
    "zh-CN-YunyangNeural":    "云扬 - 专业男声（播音腔，新闻/播报）",
    "zh-CN-YunjianNeural":    "云健 - 低沉男声（成熟，广告/纪录片）",
    "zh-CN-YunxiaNeural":     "云夏 - 少年男声（阳光，适合青年内容）",
    "zh-CN-YunfengNeural":    "云枫 - 沉稳男声（稳重，企业/正式）",
    "zh-CN-YunhaoNeural":     "云浩 - 浑厚男声（大气，宣传片）",
    "zh-CN-YunyeNeural":      "云野 - 磁性男声（成熟，情感/深夜电台）",
    "zh-CN-YunzeNeural":      "云泽 - 温和男声（亲切，客服/解说）",
}


def fail(message):
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    sys.exit(1)


def parse_args():
    p = argparse.ArgumentParser(description="dsh-ai-voice TTS 语音合成")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--text", help="要合成的文本内容")
    src.add_argument("--file", help="从文本文件读取内容")
    p.add_argument("--out", default=None, help="输出 MP3 文件路径")
    p.add_argument("--voice", default="zh-CN-XiaoxiaoNeural",
                   help="音色名称，默认 zh-CN-XiaoxiaoNeural")
    p.add_argument("--rate", default="+0%",
                   help='语速调整，如 "+10%" / "-5%"，默认 +0%')
    p.add_argument("--pitch", default="+0Hz",
                   help='音调调整，如 "+5Hz" / "-3Hz"，默认 +0Hz')
    p.add_argument("--volume", default="+0%",
                   help='音量调整，如 "+20%" / "-10%"，默认 +0%')
    p.add_argument("--list-voices", action="store_true",
                   help="列出所有可用中文音色后退出")
    return p.parse_args()


async def synthesize_once(text, voice, rate, pitch, volume, out_path):
    """调用 edge-tts 合成一段文本，写入 out_path。"""
    try:
        import edge_tts
    except ImportError:
        fail(
            "缺少依赖 edge-tts，请先安装：\n"
            "  pip install edge-tts\n"
            "安装后重新运行本脚本。"
        )

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
        volume=volume,
    )
    await communicate.save(out_path)


def split_text(text, max_chars=300):
    """将长文本按句子切分，每段不超过 max_chars 字。"""
    import re
    sentences = re.split(r"(?<=[。！？!?；;\n])", text)
    chunks = []
    buf = ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(buf) + len(s) <= max_chars:
            buf += s
        else:
            if buf:
                chunks.append(buf)
            while len(s) > max_chars:
                chunks.append(s[:max_chars])
                s = s[max_chars:]
            buf = s
    if buf:
        chunks.append(buf)
    return chunks


async def run(text, voice, rate, pitch, volume, out_path):
    chunks = split_text(text)
    if not chunks:
        fail("文本内容为空")

    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    if len(chunks) == 1:
        await synthesize_once(chunks[0], voice, rate, pitch, volume, out_path)
    else:
        tmp_files = []
        try:
            for i, chunk in enumerate(chunks):
                tmp = tempfile.NamedTemporaryFile(
                    suffix=f"_part{i:03d}.mp3", delete=False)
                tmp.close()
                tmp_files.append(tmp.name)
                await synthesize_once(chunk, voice, rate, pitch, volume, tmp.name)
            with open(out_path, "wb") as out_f:
                for tf in tmp_files:
                    with open(tf, "rb") as in_f:
                        out_f.write(in_f.read())
        finally:
            for tf in tmp_files:
                try:
                    os.unlink(tf)
                except OSError:
                    pass

    size = os.path.getsize(out_path)
    result = {
        "ok": True,
        "output": out_path,
        "voice": voice,
        "rate": rate,
        "pitch": pitch,
        "volume": volume,
        "text_length": len(text),
        "chunks": len(chunks),
        "file_size_bytes": size,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    args = parse_args()

    if not args.text and not args.file and not args.list_voices:
        fail("必须提供 --text 或 --file（或使用 --list-voices 查看音色）")

    if args.list_voices:
        print(json.dumps(ZH_VOICES, ensure_ascii=False, indent=2))
        return

    if not args.out:
        fail("--out 为必填项（除非使用 --list-voices）")

    if args.file:
        fp = os.path.abspath(args.file)
        if not os.path.isfile(fp):
            fail(f"文本文件不存在: {fp}")
        with open(fp, "r", encoding="utf-8") as f:
            text = f.read().strip()
    else:
        text = args.text.strip()

    if not text:
        fail("文本内容为空")

    asyncio.run(run(text, args.voice, args.rate, args.pitch, args.volume, args.out))


if __name__ == "__main__":
    main()
