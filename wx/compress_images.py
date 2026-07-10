#!/usr/bin/env python3
"""压缩当前脚本所在目录下所有子文件夹里的图片，输出到同级的 new 目录。

用法:
    python3 compress_images.py

直接双击或 python3 运行即可：
    - 遍历脚本所在目录下的所有子文件夹（跳过 new 目录本身）
    - 压缩找到的图片，保持原有目录结构输出到 ./new/ 下
    - 原图不会被修改或删除
"""

from pathlib import Path

from PIL import Image

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
QUALITY = 75
MAX_SIZE = 512


def compress_image(src: Path, dst: Path) -> tuple[int, int]:
    dst = dst.with_suffix(".jpg")
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        original_size = src.stat().st_size

        if img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")

        if max(img.size) > MAX_SIZE:
            img.thumbnail((MAX_SIZE, MAX_SIZE), Image.LANCZOS)

        img.save(dst, "JPEG", quality=QUALITY, optimize=True)

    compressed_size = dst.stat().st_size
    return original_size, compressed_size


def find_images(root: Path, output_dir: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
            if output_dir in path.parents:
                continue
            yield path


def main():
    root = Path(__file__).resolve().parent
    output_dir = root / "new"

    images = list(find_images(root, output_dir))
    if not images:
        print("未找到可压缩的图片")
        return

    total_original = 0
    total_compressed = 0

    for src in images:
        rel = src.relative_to(root)
        dst = output_dir / rel
        try:
            original_size, compressed_size = compress_image(src, dst)
        except Exception as e:
            print(f"跳过 {rel}: {e}")
            continue

        total_original += original_size
        total_compressed += compressed_size
        ratio = (1 - compressed_size / original_size) * 100 if original_size else 0
        print(f"{rel}: {original_size / 1024:.1f}KB -> {compressed_size / 1024:.1f}KB ({ratio:.1f}%)")

    if total_original:
        total_ratio = (1 - total_compressed / total_original) * 100
        print(f"\n共处理 {len(images)} 张图片，总体积 {total_original / 1024:.1f}KB -> {total_compressed / 1024:.1f}KB (压缩 {total_ratio:.1f}%)")

    print(f"结果已输出到: {output_dir}")


if __name__ == "__main__":
    main()
