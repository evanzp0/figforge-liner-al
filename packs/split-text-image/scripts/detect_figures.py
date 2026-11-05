#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""figforge :: pack-1 split-text-image —— 单页插图检测与裁剪

用法:
  # A. 自动: z-ai vision 检测插图包围盒（串行, 由 runner.py 逐页调度 —— 宪法第三条）
  detect_figures.py --page 0107 --image in/0107.png --out build/0107
  # B. 手工兜底: 已知框时跳过 API（框格式 "x,y,w,h;x,y,w,h"）
  detect_figures.py --page 0107 --image in/0107.png --out build/0107 \
      --boxes "60,150,760,380;0,0,200,120"

输出:
  <out>/figures.json        [{"idx":1,"bbox":[x,y,w,h],"caption":"..."}]
  <out>/crops/fig1.jpg ...  裁剪 JPG（quality=92, 四周 pad 留白）

宪法约束:
  * 第三条: 本脚本一次只处理一页, 并发调度交给 runner.py（恒定单进程）;
  * 第六条: 检测到 429/Too Many Requests → 退出码 43 熔断（不硬重试、不换通道）,
    由 runner 停批并转 probe-429.sh 低频探测;
  * 第十一条: vision 响应等临时文件一律写 figforge/.work/tmp/（complete.sh 收尾时
    整目录清理, 临时内容不进交付包）。
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # figforge/


def work_tmp() -> str:
    """宪法第十一条: 临时文件一律进 figforge/.work/tmp/。"""
    d = os.path.join(ROOT, ".work", "tmp")
    os.makedirs(d, exist_ok=True)
    return d


VISION_PROMPT = (
    "Find all illustrations/diagrams/figures on this scanned textbook page "
    "(ignore pure text paragraphs, headers, page numbers). "
    'Reply with STRICT JSON only: {"figures":[{"bbox":[x,y,width,height],"caption":"..."}]} '
    "where bbox is in pixels of the original image, ordered top-left to bottom-right. "
    "If there are no figures, reply {\"figures\":[]}. No markdown fences, no extra text."
)


def parse_boxes(spec: str):
    boxes = []
    for part in spec.split(";"):
        part = part.strip()
        if not part:
            continue
        nums = [int(round(float(v))) for v in part.replace(" ", "").split(",")]
        if len(nums) != 4:
            raise SystemExit(f"--boxes 段非法: {part!r}（应为 x,y,w,h）")
        boxes.append({"bbox": nums, "caption": "manual"})
    return boxes


def extract_figures_payload(text: str, _depth: int = 0):
    """从 vision 输出中尽力提取 {"figures":[...]}。

    容忍三类包装: ①markdown 围栏 / 前后杂文本; ②z-ai -o 保存的完整
    chat.completion 响应（正文在 choices[0].message.content, 递归解析）;
    ③{"content": "...json..."} 之类的字符串包装。
    """
    if _depth > 4 or not text or not text.strip():
        return None
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        obj = json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return None
        try:
            obj = json.loads(m.group(0))
        except Exception:
            return None
    if isinstance(obj, dict):
        if "figures" in obj and isinstance(obj["figures"], list):
            return obj["figures"]
        if "choices" in obj and isinstance(obj["choices"], list):  # chat.completion
            for ch in obj["choices"]:
                msg = (ch.get("message") if isinstance(ch, dict) else None) or {}
                content = msg.get("content")
                if isinstance(content, str) and "figures" in content:
                    got = extract_figures_payload(content, _depth + 1)
                    if got is not None:
                        return got
        for v in obj.values():  # 某些包装: {"content": "...json..."}
            if isinstance(v, str) and '"figures"' in v:
                got = extract_figures_payload(v, _depth + 1)
                if got is not None:
                    return got
    return None


def vision_detect(image_path: str):
    """调用 z-ai vision; 429 → 退出码 43（宪法第六条）。"""
    fd, out_path = tempfile.mkstemp(suffix=".json", dir=work_tmp())
    os.close(fd)
    try:
        p = subprocess.run(
            ["z-ai", "vision", "-p", VISION_PROMPT, "-i", image_path, "-o", out_path],
            capture_output=True, text=True, timeout=180,
        )
        blob = ""
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            blob = open(out_path, encoding="utf-8", errors="replace").read()
        if not blob.strip():
            blob = (p.stdout or "") + "\n" + (p.stderr or "")
        joined = blob[:200000]
        if p.returncode != 0 and ("429" in joined or "Too Many Requests" in joined):
            print("[detect_figures] 429 风暴（宪法第六条）→ 熔断退出码 43", file=sys.stderr)
            raise SystemExit(43)
        if p.returncode != 0:
            print(f"[detect_figures] vision 失败 rc={p.returncode}: {joined[:400]}", file=sys.stderr)
            raise SystemExit(p.returncode or 1)
        figs = extract_figures_payload(joined)
        if figs is None:
            print("[detect_figures] 无法解析 vision 输出为 JSON; 请改用 --boxes 兜底", file=sys.stderr)
            raise SystemExit(2)
        return figs
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


def crop_all(image_path: str, figures, out_dir: str, pad: int, quality: int):
    img = Image.open(image_path).convert("RGB")
    W, H = img.size
    crops_dir = os.path.join(out_dir, "crops")
    os.makedirs(crops_dir, exist_ok=True)
    records = []
    for i, f in enumerate(figures, 1):
        x, y, w, h = f["bbox"]
        x0, y0 = max(0, x - pad), max(0, y - pad)
        x1, y1 = min(W, x + w + pad), min(H, y + h + pad)
        if x1 <= x0 or y1 <= y0:
            print(f"[detect_figures] 跳过非法框 {f['bbox']}", file=sys.stderr)
            continue
        img.crop((x0, y0, x1, y1)).save(
            os.path.join(crops_dir, f"fig{i}.jpg"), quality=quality
        )
        records.append({"idx": len(records) + 1, "bbox": [x0, y0, x1 - x0, y1 - y0],
                        "caption": f.get("caption", "")})
    return records


def main():
    ap = argparse.ArgumentParser(description="pack-1: 插图检测与裁剪（单页）")
    ap.add_argument("--page", required=True, help="页号, 如 0107")
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True, help="输出目录, 如 build/0107")
    ap.add_argument("--boxes", default=None, help="手工框 'x,y,w,h;x,y,w,h'（跳过 API）")
    ap.add_argument("--pad", type=int, default=6, help="裁剪四周留白 px")
    ap.add_argument("--quality", type=int, default=92)
    a = ap.parse_args()

    if not os.path.exists(a.image):
        raise SystemExit(f"detect_figures: 找不到 {a.image}")

    os.makedirs(a.out, exist_ok=True)
    if a.boxes:
        figures = parse_boxes(a.boxes)
        source = "manual"
    else:
        figures = vision_detect(a.image) or []
        source = "z-ai-vision"

    records = crop_all(a.image, figures, a.out, a.pad, a.quality)
    meta = {"page": a.page, "source": source, "count": len(records), "figures": records}
    with open(os.path.join(a.out, "figures.json"), "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False, indent=1)
    print(f"[detect_figures] {a.page}: {len(records)} 张插图 → {a.out}/crops/")


if __name__ == "__main__":
    main()
