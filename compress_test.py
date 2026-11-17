#!/usr/bin/env python3
"""压缩试效果：拿几张图跑一组画质档位，输出到独立目录供肉眼对比。

只读原图，不改不删，输出目录是独立的，不会碰 old / new / wx-food。

用法
----
    # 最省事：递归扫描 old/ 下所有嵌套图片，全部跑「正式脚本同款档」+ 几个对比档
    python3 compress_test.py

    # 只试某一类（按目录名过滤，和 compress_images.py 的 --only 一个意思）
    python3 compress_test.py --only food-cook

    # 指定图片（可以多张，也可以给目录，目录会递归进嵌套层）
    python3 compress_test.py old/番茄炒蛋.jpg old/土豆炖鸡.png
    python3 compress_test.py old/food-cook

    # 指定多档画质一起比
    python3 compress_test.py old/番茄炒蛋.jpg --quality 75 82 88

    # 顺便比一下缩小尺寸的效果
    python3 compress_test.py old/番茄炒蛋.jpg --resize 640

跑完会打印一张对比表，并告诉你输出文件在哪，双击就能看。

关键点：默认会额外跑一档「prod」（= compress_images.py 的真实档位），
        试跑看到的画质/体积就是批量跑出来的结果，不会出现「试的时候清楚、
        批量跑完糊了」这种事。prod 档直接复用 compress_images.py 的
        PROFILES / pick_profile，改正式脚本参数这里会自动跟着变。
"""

from __future__ import annotations

import argparse
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps

from compress_images import PROFILES, pick_profile

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}

# 默认对比档：78 是「能接受的最小」，82 是推荐档，88 用来确认上限
DEFAULT_QUALITIES = (78, 82, 88)
# 不传 --resize 就按原分辨率压，海报缩宽会把中文小字糊掉
DEFAULT_WIDTHS = (0,)


def collect(targets: list[str], fallback_dir: Path, only: str | None = None) -> list[Path]:
    """把命令行给的路径摊平成图片列表；没给就退回 fallback_dir 递归取全部。

    和 compress_images.py 的 find_images 一样：
      - 给目录 → rglob 递归进所有嵌套层，处理每一张；
      - 不给参数 → 默认递归扫描 fallback_dir（old/）下全部图片，不再只取前 2 张；
      - only 非空 → 只保留路径里含该目录名的图（同 --only，比如 food-cook）。
    """
    found: list[Path] = []

    for item in targets:
        p = Path(item)
        if p.is_dir():
            found.extend(sorted(x for x in p.rglob("*") if x.suffix.lower() in SUPPORTED_EXTS))
        elif p.is_file():
            found.append(p)
        else:
            print(f"跳过不存在的路径: {item}")

    if not found and fallback_dir.is_dir():
        found = sorted(x for x in fallback_dir.rglob("*") if x.suffix.lower() in SUPPORTED_EXTS)

    if only:
        found = [x for x in found if only in x.parts]

    return found


def load(src: Path) -> Image.Image:
    """读图并统一成 RGB；顺手按 EXIF 转正，否则竖拍图会躺倒。"""
    img = Image.open(src)
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    return img


def encode(img: Image.Image, quality: int) -> bytes:
    """编码成 JPEG；参数与 compress_images.py 完全一致。"""
    buf = BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True, progressive=True)
    return buf.getvalue()


def prod_variant(img: Image.Image, src: Path, root: Path) -> tuple[bytes, str]:
    """完全复刻 compress_images.py 的处理：按路径选档、长边限制、指定画质。"""
    try:
        rel = src.relative_to(root)
    except ValueError:
        rel = Path(src.name)

    profile = pick_profile(rel)
    out = img.copy()

    # 正式脚本用 thumbnail（长边上限、只缩不放），这里必须一样
    if max(out.size) > profile.max_size:
        out.thumbnail((profile.max_size, profile.max_size), Image.LANCZOS)

    return encode(out, profile.quality), f"{out.width}×{out.height} q{profile.quality}"


def main() -> int:
    parser = argparse.ArgumentParser(description="对比不同压缩档位下的体积与效果")
    parser.add_argument("targets", nargs="*", help="图片或目录；留空则取 old/ 前 2 张")
    parser.add_argument("--quality", "-q", nargs="+", type=int, default=list(DEFAULT_QUALITIES),
                        help=f"JPEG 画质，可给多档：{' '.join(map(str, DEFAULT_QUALITIES))}")
    parser.add_argument("--resize", "-w", nargs="+", type=int, default=list(DEFAULT_WIDTHS),
                        help="目标宽度，可给多档；0 或不传=保持原分辨率")
    parser.add_argument("--out", "-o", default="compress_preview", help="输出目录，默认 compress_preview/")
    parser.add_argument("--only", default=None, help="只处理路径里含该目录名的图，比如 food-cook（同 compress_images.py）")
    parser.add_argument("--no-prod", action="store_true", help="不跑「正式脚本同款档」，只比自定义档位")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    sources = collect(args.targets, root / "old", only=args.only)

    if not sources:
        print("没找到图片。把想试的图放进 old/ ，或者直接用路径指定：")
        print("  python3 compress_test.py 你的图.jpg")
        return 1

    out_dir = (root / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"待测 {len(sources)} 张，输出到 {out_dir}")
    print("prod = compress_images.py 的真实档位，看这一档就等于看批量结果\n")

    grand_src = 0
    grand_prod = 0

    for src in sources:
        img = load(src)
        original = src.stat().st_size
        grand_src += original

        # 输出文件名按「相对脚本目录的路径」拼，避免嵌套目录里同名文件互相覆盖。
        try:
            base = str(src.relative_to(root).with_suffix("")).replace("/", "__")
        except ValueError:
            base = src.stem

        print(f"{src.name}   原图 {original / 1024:.0f} KB  ·  {img.width}×{img.height}")

        prod_size = None
        if not args.no_prod:
            try:
                data, label = prod_variant(img, src, root)
                (out_dir / f"{base}__prod.jpg").write_bytes(data)
                prod_size = len(data)
                ratio = (1 - prod_size / original) * 100
                print(f"    {'prod':<12} {prod_size / 1024:6.0f} KB   降 {ratio:4.1f}%   {label}   ← 批量脚本会用这档")
            except Exception as exc:  # noqa: BLE001 - 单张失败不该中断整批
                print(f"    prod 失败: {exc}")

        for width in args.resize:
            if width and width > img.width:
                continue
            out = img
            if width:
                ratio = width / img.width
                out = img.resize((width, max(1, round(img.height * ratio))), Image.LANCZOS)

            for q in args.quality:
                tag = f"w{width}_q{q}" if width else f"q{q}"
                try:
                    data = encode(out, q)
                except Exception as exc:  # noqa: BLE001
                    print(f"    {tag}  失败: {exc}")
                    continue

                (out_dir / f"{base}__{tag}.jpg").write_bytes(data)
                ratio = (1 - len(data) / original) * 100
                flag = "  ← 比原图还大，别用" if len(data) >= original else ""
                print(f"    {tag:<12} {len(data) / 1024:6.0f} KB   降 {ratio:4.1f}%   宽 {width or img.width}{flag}")

        grand_prod += prod_size or original
        print("")

    if grand_src:
        print(f"合计（按 prod 档）{grand_src / 1024:.0f} KB → {grand_prod / 1024:.0f} KB，"
              f"降 {(1 - grand_prod / grand_src) * 100:.1f}%")
    print(f"对比图已输出到: {out_dir}")
    print("先打开 __prod.jpg 确认中文小字还清楚，再跑 python3 compress_images.py 批量。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
