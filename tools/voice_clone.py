#!/usr/bin/env python3
"""聲音克隆朗讀：用 CosyVoice 2 把每日新聞摘要唸成語音，嵌進日報頁面。

模型選 CosyVoice 2（FunAudioLLM/CosyVoice，開源）：3～10 秒樣本即可零樣本克隆，
中文與中英混讀表現在公開比較裡名列前茅，且能切段合成，長文不易爆記憶體。
需要 GPU（建議 8GB VRAM 以上），雲端排程沙盒跑不動，請在本機或 GPU 主機執行。

一次性安裝（見 requirements-voice.txt 與 README「聲音克隆」）：
    git clone --recursive https://github.com/FunAudioLLM/CosyVoice ~/CosyVoice
    export COSYVOICE_DIR=~/CosyVoice

用法：
    # 1. 登記聲音（一定要先聲明授權，見下方「授權」）
    python3 tools/voice_clone.py enroll me --sample me.wav \\
        --transcript "樣本裡實際唸的那句話" --consent self

    # 2. 朗讀當天日報（預設今日焦點 3 則；--all-top 加上全球前 10）
    python3 tools/voice_clone.py speak 2026-08-26 --voice me

    # 3. 朗讀任意文字
    python3 tools/voice_clone.py speak --text "大家好" --voice me --out hello.mp3

    # 4. 組版時 build.py 偵測到 dist/audio/<日期>.mp3 就會自動嵌入播放器
    python3 build.py 2026-08-26

授權：
    只能克隆「你本人」或「已取得書面授權」的聲音。enroll 必須帶
    --consent self（本人）或 --consent licensed --license-doc <授權文件路徑>，
    授權聲明與樣本 SHA-256 會寫進 voices/<名稱>/meta.json。沒有登記過的聲音
    不能拿來合成。輸出的 MP3 會寫入「AI 合成語音」標籤，頁面播放器也會標示。
    voices/ 含個人聲紋，已加入 .gitignore，不要 commit。
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICES = os.path.join(ROOT, "voices")
AUDIO = os.path.join(ROOT, "dist", "audio")
MODEL = "CosyVoice2-0.5B"
MAX_CHARS = 80  # 單段上限：切短才不會 OOM，語氣也比較穩
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")


def die(msg):
    print(f"錯誤：{msg}", file=sys.stderr)
    sys.exit(1)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def split_text(text, limit=MAX_CHARS):
    """依句讀切段，每段不超過 limit 字；過長的句子再依逗號硬切。"""
    text = re.sub(r"\s+", " ", text).strip()
    sentences = [s for s in re.split(r"(?<=[。！？!?；;])", text) if s.strip()]
    chunks, cur = [], ""
    for s in sentences:
        while len(s) > limit:
            cut = max(s.rfind(p, 0, limit) for p in "，,、 ")
            cut = cut + 1 if cut > 0 else limit
            s, rest = s[:cut], s[cut:]
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(s)
            s = rest
        if len(cur) + len(s) > limit and cur:
            chunks.append(cur)
            cur = ""
        cur += s
    if cur.strip():
        chunks.append(cur)
    return [c.strip() for c in chunks if c.strip()]


def date_script(date, include_global=False):
    """把當天資料整理成朗讀稿：開場白＋每則「標題。摘要」。"""
    path = os.path.join(ROOT, "data", f"{date}.json")
    if not os.path.exists(path):
        die(f"找不到 {path}")
    data = json.load(open(path, encoding="utf-8"))
    d = datetime.strptime(date, "%Y-%m-%d")
    parts = [f"豬豬日報，{d.month}月{d.day}日今日焦點。"]
    items = list(data["top3"]) + (data["global"][:10] if include_global else [])
    for i, it in enumerate(items, 1):
        parts.append(f"第{i}則。{it['title']}。{it.get('summary', '')}")
    return "\n".join(parts)


# ── 登記 ────────────────────────────────────────────────────────────────

def cmd_enroll(a):
    if not NAME_RE.match(a.name):
        die("聲音名稱只能用英數、底線、連字號")
    if not os.path.isfile(a.sample):
        die(f"找不到樣本檔 {a.sample}")
    if a.consent == "licensed":
        if not a.license_doc or not os.path.isfile(a.license_doc):
            die("--consent licensed 必須附 --license-doc <授權文件檔案>")
    if len(a.transcript.strip()) < 4:
        die("--transcript 要寫樣本裡實際唸的內容（用來對齊音色，不能亂填）")

    dest = os.path.join(VOICES, a.name)
    if os.path.exists(dest) and not a.force:
        die(f"{a.name} 已存在，要覆蓋請加 --force")
    os.makedirs(dest, exist_ok=True)

    wav = os.path.join(dest, "sample.wav")
    if shutil.which("ffmpeg"):
        # 統一成 16 kHz 單聲道，最長取 30 秒；CosyVoice 只需要幾秒
        r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.sample,
                            "-t", "30", "-ar", "16000", "-ac", "1", wav])
        if r.returncode:
            die("ffmpeg 轉檔失敗，請確認樣本是有效的音訊檔")
    elif a.sample.lower().endswith(".wav"):
        shutil.copy(a.sample, wav)
    else:
        die("非 wav 樣本需要 ffmpeg 才能轉檔")

    meta = {
        "name": a.name,
        "transcript": a.transcript.strip(),
        "consent": a.consent,
        "license_doc_sha256": sha256(a.license_doc) if a.license_doc else None,
        "sample_sha256": sha256(wav),
        "enrolled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    json.dump(meta, open(os.path.join(dest, "meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"已登記聲音 {a.name}（授權：{a.consent}）→ {dest}")


def load_voice(name):
    d = os.path.join(VOICES, name)
    meta_path = os.path.join(d, "meta.json")
    if not os.path.isfile(meta_path):
        die(f"聲音 {name} 尚未登記；請先 enroll（需聲明授權）")
    meta = json.load(open(meta_path, encoding="utf-8"))
    wav = os.path.join(d, "sample.wav")
    if not os.path.isfile(wav) or sha256(wav) != meta["sample_sha256"]:
        die("樣本檔遺失或與登記時不符，請重新 enroll")
    if meta.get("consent") not in ("self", "licensed"):
        die("授權紀錄不完整，請重新 enroll")
    return meta, wav


# ── 合成 ────────────────────────────────────────────────────────────────

def load_model():
    root = os.environ.get("COSYVOICE_DIR")
    if not root or not os.path.isdir(root):
        die("請先設定 COSYVOICE_DIR 指向 CosyVoice 的 clone 目錄（見 README「聲音克隆」）")
    sys.path[:0] = [root, os.path.join(root, "third_party", "Matcha-TTS")]
    model_dir = os.environ.get("COSYVOICE_MODEL") or os.path.join(root, "pretrained_models", MODEL)
    if not os.path.isdir(model_dir):
        die(f"找不到模型 {model_dir}；請依 CosyVoice 官方說明下載 {MODEL}")
    try:
        from cosyvoice.cli.cosyvoice import CosyVoice2
        from cosyvoice.utils.file_utils import load_wav
    except ImportError as exc:
        die(f"載入 CosyVoice 失敗（{exc}）；請依 requirements-voice.txt 安裝依賴")
    return CosyVoice2(model_dir, load_jit=False, load_trt=False, fp16=True), load_wav


def synthesize(text, meta, wav, out):
    import torch
    import torchaudio

    model, load_wav = load_model()
    prompt = load_wav(wav, 16000)
    pieces = []
    chunks = split_text(text)
    for i, chunk in enumerate(chunks, 1):
        print(f"  [{i}/{len(chunks)}] {chunk[:30]}…")
        for seg in model.inference_zero_shot(chunk, meta["transcript"], prompt, stream=False):
            pieces.append(seg["tts_speech"])
        # 段落間留 0.25 秒空白
        pieces.append(torch.zeros(1, int(model.sample_rate * 0.25)))
    audio = torch.cat(pieces, dim=1)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    if out.lower().endswith(".mp3"):
        if not shutil.which("ffmpeg"):
            die("輸出 mp3 需要 ffmpeg；或改用 .wav")
        tmp = out + ".tmp.wav"
        torchaudio.save(tmp, audio, model.sample_rate)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", tmp,
                        "-metadata", "comment=AI 合成語音（聲音克隆，已取得授權）",
                        "-metadata", "artist=豬豬日報 AI 語音",
                        "-b:a", "64k", "-ac", "1", out], check=True)
        os.remove(tmp)
    else:
        torchaudio.save(out, audio, model.sample_rate)
    print(f"→ {out}  {audio.shape[1] / model.sample_rate:.0f} 秒")


def cmd_speak(a):
    meta, wav = load_voice(a.voice)
    if a.text:
        text, out = a.text, a.out or os.path.join(AUDIO, "speech.mp3")
    elif a.date:
        text = date_script(a.date, a.all_top)
        out = a.out or os.path.join(AUDIO, f"{a.date}.mp3")
    else:
        die("請給日期或 --text")
    if a.dry_run:
        for i, c in enumerate(split_text(text), 1):
            print(f"{i:>2}. {c}")
        return
    synthesize(text, meta, wav, out)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("enroll", help="登記聲音樣本（需聲明授權）")
    e.add_argument("name")
    e.add_argument("--sample", required=True, help="3～30 秒乾淨的單人錄音")
    e.add_argument("--transcript", required=True, help="樣本裡實際唸的文字")
    e.add_argument("--consent", required=True, choices=["self", "licensed"],
                   help="self=我本人的聲音；licensed=已取得書面授權")
    e.add_argument("--license-doc", help="consent=licensed 時必填：授權文件檔")
    e.add_argument("--force", action="store_true")
    e.set_defaults(fn=cmd_enroll)

    s = sub.add_parser("speak", help="用已登記的聲音朗讀")
    s.add_argument("date", nargs="?", help="YYYY-MM-DD，朗讀當天日報")
    s.add_argument("--text", help="改為朗讀這段文字")
    s.add_argument("--voice", required=True)
    s.add_argument("--out")
    s.add_argument("--all-top", action="store_true", help="今日焦點之外再加全球前 10 則")
    s.add_argument("--dry-run", action="store_true", help="只印出切段結果，不載入模型")
    s.set_defaults(fn=cmd_speak)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
