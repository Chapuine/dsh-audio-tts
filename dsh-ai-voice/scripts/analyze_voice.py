#!/usr/bin/env python3
"""dsh-ai-voice 音色识别脚本。

分析参考音频，提取声学特征并推断音色画像：
- 基频 F0 统计（均值 / 中位数 / 范围）→ 性别、年龄感
- 语速估计 → 说话节奏快慢
- RMS 能量 / 响度 → 音量风格
- 频谱质心 / 带宽 → 声音明亮度
- F0 动态范围 → 情感起伏程度
- 综合推断：性别、年龄段、音色类型、情感风格、推荐 TTS 音色与参数

输出 JSON，供上层模型（DeepSeek）阅读后做参数决策。

用法：
    python3 analyze_voice.py /path/to/reference.wav
    python3 analyze_voice.py /path/to/ref.mp3 --output result.json
"""

import argparse
import json
import os
import sys


def fail(message):
    print(json.dumps({"ok": False, "error": message}, ensure_ascii=False))
    sys.exit(1)


def parse_args():
    p = argparse.ArgumentParser(description="dsh-ai-voice 音色识别")
    p.add_argument("input", help="参考音频路径（wav / mp3 / flac / ogg / m4a）")
    p.add_argument("--output", default=None, help="将完整结果写入指定 JSON 文件")
    p.add_argument("--sr", type=int, default=16000, help="重采样采样率，默认 16000")
    return p.parse_args()


def safe_float(v, ndigits=2):
    try:
        if v is None:
            return None
        import math
        if math.isnan(v) or math.isinf(v):
            return None
        return round(float(v), ndigits)
    except Exception:
        return None


def main():
    args = parse_args()
    src = os.path.abspath(args.input)
    if not os.path.isfile(src):
        fail(f"音频文件不存在: {src}")

    try:
        import librosa
        import numpy as np
    except ImportError:
        fail(
            "缺少依赖 librosa / numpy，请先安装：\n"
            "  pip install librosa numpy soundfile\n"
            "安装后重新运行本脚本。"
        )

    # ---------- 加载音频 ----------
    try:
        y, sr = librosa.load(src, sr=args.sr, mono=True)
    except Exception as e:
        fail(f"音频加载失败: {e}")

    duration = float(len(y) / sr)
    if duration < 0.3:
        fail(f"音频过短（{duration:.2f}s），至少需要 0.3 秒以上才能分析")

    # ---------- 基频 F0 ----------
    f0_series, voiced_flag, _ = librosa.pyin(
        y, fmin=librosa.note_to_hz("C2"), fmax=librosa.note_to_hz("C7"), sr=sr
    )
    f0_voiced = f0_series[~np.isnan(f0_series)]
    if len(f0_voiced) < 10:
        fail("无法从音频中提取有效基频，请确认是清晰的人声录音")

    f0_mean = float(np.mean(f0_voiced))
    f0_median = float(np.median(f0_voiced))
    f0_std = float(np.std(f0_voiced))
    f0_min = float(np.min(f0_voiced))
    f0_max = float(np.max(f0_voiced))
    voiced_ratio = float(np.sum(voiced_flag)) / len(voiced_flag)

    # ---------- 性别推断 ----------
    if f0_median < 165:
        gender = "male"
        gender_cn = "男性"
    elif f0_median > 175:
        gender = "female"
        gender_cn = "女性"
    else:
        gender = "unknown"
        gender_cn = "中性/不确定"

    # ---------- 年龄感 ----------
    if f0_median < 120:
        age_hint = "成熟/低沉（偏中老年）"
    elif f0_median < 160:
        age_hint = "成熟稳重（中青年）"
    elif f0_median < 210:
        age_hint = "青年"
    else:
        age_hint = "年轻/童声感"

    # ---------- 语速估计 ----------
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_frames = librosa.onset.onset_detect(
        onset_envelope=onset_env, sr=sr, backtrack=True
    )
    n_syllables = len(onset_frames)
    syllables_per_sec = n_syllables / duration if duration > 0 else 0

    if syllables_per_sec < 3.5:
        speed = "slow"
        speed_cn = "偏慢（沉稳/舒缓）"
        rate_pct = "-10%"
    elif syllables_per_sec < 5.0:
        speed = "normal"
        speed_cn = "正常语速"
        rate_pct = "+0%"
    elif syllables_per_sec < 6.5:
        speed = "fast"
        speed_cn = "偏快（干练/活力）"
        rate_pct = "+10%"
    else:
        speed = "very_fast"
        speed_cn = "很快（急促/激情）"
        rate_pct = "+20%"

    # ---------- 能量 / 响度 ----------
    rms = librosa.feature.rms(y=y)[0]
    rms_mean = float(np.mean(rms))
    rms_std = float(np.std(rms))
    loudness = min(100, max(0, round(rms_mean * 300)))

    if rms_mean < 0.02:
        volume = "soft"
        volume_cn = "轻柔/小声"
    elif rms_mean < 0.08:
        volume = "normal"
        volume_cn = "正常音量"
    else:
        volume = "loud"
        volume_cn = "洪亮/有力"

    # ---------- 频谱质心（声音亮度） ----------
    cent = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    cent_mean = float(np.mean(cent))
    if cent_mean < 1500:
        brightness = "warm"
        brightness_cn = "温暖/浑厚"
    elif cent_mean < 2500:
        brightness = "neutral"
        brightness_cn = "自然/适中"
    else:
        brightness = "bright"
        brightness_cn = "明亮/清脆"

    # ---------- 情感风格推断 ----------
    f0_dynamics = f0_std / f0_mean if f0_mean > 0 else 0
    energy_dynamics = rms_std / rms_mean if rms_mean > 0 else 0

    if f0_dynamics > 0.25 or energy_dynamics > 0.6:
        emotion = "expressive"
        emotion_cn = "情感丰富 / 起伏明显"
    elif f0_dynamics > 0.12:
        emotion = "moderate"
        emotion_cn = "自然适中 / 有轻微起伏"
    else:
        emotion = "calm"
        emotion_cn = "平稳克制 / 沉稳叙述"

    # ---------- 推荐 Edge TTS 音色 ----------
    zh_voices = {
        ("male", "warm"): "zh-CN-YunjianNeural",
        ("male", "neutral"): "zh-CN-YunxiNeural",
        ("male", "bright"): "zh-CN-YunyangNeural",
        ("female", "warm"): "zh-CN-XiaoxiaoNeural",
        ("female", "neutral"): "zh-CN-XiaoyiNeural",
        ("female", "bright"): "zh-CN-XiaochenNeural",
    }
    fallback_voice = "zh-CN-XiaoxiaoNeural" if gender == "female" else "zh-CN-YunxiNeural"
    recommended_voice = zh_voices.get((gender, brightness), fallback_voice)

    # 音调调整
    if gender == "male":
        pitch_shift_hz = f0_median - 120
    elif gender == "female":
        pitch_shift_hz = f0_median - 210
    else:
        pitch_shift_hz = 0
    pitch_hz = int(max(-50, min(50, pitch_shift_hz * 0.3)))

    result = {
        "ok": True,
        "input": src,
        "duration_sec": safe_float(duration, 2),
        "sample_rate": sr,
        "voice_profile": {
            "gender": gender,
            "gender_cn": gender_cn,
            "age_hint": age_hint,
            "f0_hz": {
                "median": safe_float(f0_median, 1),
                "mean": safe_float(f0_mean, 1),
                "std": safe_float(f0_std, 1),
                "range": [safe_float(f0_min, 1), safe_float(f0_max, 1)],
                "voiced_ratio": safe_float(voiced_ratio, 2),
            },
            "speaking_rate": {
                "level": speed,
                "label_cn": speed_cn,
                "syllables_per_sec": safe_float(syllables_per_sec, 2),
                "edge_rate_hint": rate_pct,
            },
            "volume": {
                "level": volume,
                "label_cn": volume_cn,
                "loudness_0_100": loudness,
            },
            "timbre": {
                "brightness": brightness,
                "label_cn": brightness_cn,
                "spectral_centroid_hz": safe_float(cent_mean, 1),
            },
            "emotion_style": {
                "level": emotion,
                "label_cn": emotion_cn,
                "f0_dynamics": safe_float(f0_dynamics, 3),
                "energy_dynamics": safe_float(energy_dynamics, 3),
            },
        },
        "tts_suggestion": {
            "recommended_voice": recommended_voice,
            "rate": rate_pct,
            "pitch_hz": f"{pitch_hz:+d}Hz",
            "volume": "+0%",
            "note": "以上为基于声学特征的初始建议，上层模型可根据文本内容和用户需求进一步调整",
        },
    }

    out_json = json.dumps(result, ensure_ascii=False, indent=2)
    print(out_json)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out_json)


if __name__ == "__main__":
    main()
