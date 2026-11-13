#!/usr/bin/env python3
"""压缩当前脚本所在目录下 old 文件夹里的图片，输出到同级的 new 目录。

用法:
    python3 compress_images.py

直接双击或 python3 运行即可：
    - 遍历脚本所在目录下的所有子文件夹（跳过 new 目录本身）
    - 压缩找到的图片，保持原有目录结构输出到 ./new/ 下
    - 原图不会被修改或删除
图片压缩判断逻辑:
- 图片文件大小 > 150KB：进行缩放和 JPEG 压缩处理
- 图片文件大小 <= 150KB：直接复制到目标目录，保持原样
"""

import shutil
from pathlib import Path

from PIL import Image

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
# food
QUALITY = 80
MAX_SIZE = 512
# food-cook
# QUALITY = 100
# MAX_SIZE = 1024
SIZE_LIMIT_KB = 150  # 设定图片站内内存kb大小的阈值：150 KB


def compress_image(src: Path, dst: Path) -> tuple[int, int, str]:
    original_size = src.stat().st_size

    dst.parent.mkdir(parents=True, exist_ok=True)

    # 判断是否小于等于 150KB
    if original_size <= SIZE_LIMIT_KB * 1024:
        shutil.copy2(src, dst)
        return original_size, original_size, "跳过(小于150KB，原样复制)"

    # 大于 150KB 的图片进行压缩处理
    save_dst = dst.with_suffix(".jpg")
    
    with Image.open(src) as img:
        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        if max(img.size) > MAX_SIZE:
            img.thumbnail((MAX_SIZE, MAX_SIZE), Image.LANCZOS)

        img.save(save_dst, "JPEG", quality=QUALITY, optimize=True)

    compressed_size = save_dst.stat().st_size
    return original_size, compressed_size, "已压缩"


def find_images(root: Path, output_dir: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
            if output_dir in path.parents:
                continue
            yield path


def main():
    root = Path(__file__).resolve().parent
    input_dir = root / "wx-food/food"
    output_dir = root / "new"

    images = list(find_images(input_dir, output_dir))
    if not images:
        print("未找到可压缩的图片")
        return

    total_original = 0
    total_compressed = 0

    for src in images:
        rel = src.relative_to(input_dir)
        dst = output_dir / rel
        try:
            original_size, compressed_size, status = compress_image(src, dst)
        except Exception as e:
            print(f"跳过 {rel}: {e}")
            continue

        total_original += original_size
        total_compressed += compressed_size
        
        if "已压缩" in status:
            ratio = (1 - compressed_size / original_size) * 100 if original_size else 0
            print(f"{rel}: {original_size / 1024:.1f}KB -> {compressed_size / 1024:.1f}KB ({ratio:.1f}% 压缩)")
        else:
            print(f"{rel}: {original_size / 1024:.1f}KB -> {status}")

    if total_original:
        total_ratio = (1 - total_compressed / total_original) * 100
        print(f"\n共处理 {len(images)} 张图片，总体积 {total_original / 1024:.1f}KB -> {total_compressed / 1024:.1f}KB (压缩 {total_ratio:.1f}%)")

    print(f"结果已输出到: {output_dir}")


if __name__ == "__main__":
    main()
