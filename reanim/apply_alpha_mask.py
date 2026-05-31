#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = ["Pillow"]
# ///
"""
Apply alpha masks to images.

Usage:
    uv run apply_alpha_mask.py

For each xxx_.png (alpha mask) in the current directory, apply it to xxx.png.
Rule: final pixel alpha = 1 - grayscale_value_of_mask
  - Dark in xxx_.png → opaque in xxx.png
  - Light in xxx_.png → transparent in xxx.png
"""

from pathlib import Path
import sys

from PIL import Image


def apply_alpha_mask(mask_path: Path, src_path:Path, target_path: Path) -> bool:
    """Apply an alpha mask to a target image, modifying the target in place.

    The mask's grayscale value determines transparency:
        alpha = 1.0 - (gray / 255.0)
    So pure black (0) → fully opaque, pure white (255) → fully transparent.
    """
    try:
        # Load mask and convert to grayscale
        mask_img = Image.open(mask_path).convert("L")

        # Load target image, ensure RGBA
        target_img = Image.open(src_path).convert("RGBA")

        # If sizes differ, resize mask to match target
        if mask_img.size != target_img.size:
            print(
                f"  Warning: mask size {mask_img.size} != target size {target_img.size}, "
                f"resizing mask"
            )
            mask_img = mask_img.resize(target_img.size, Image.LANCZOS)

        # Get pixel data
        target_pixels = target_img.load()
        mask_pixels = mask_img.load()
        width, height = target_img.size

        for y in range(height):
            for x in range(width):
                gray = mask_pixels[x, y]  # 0-255
                # alpha = 1.0 - (gray / 255.0), in 8-bit: 255 - gray
                new_alpha = gray
                r, g, b, _ = target_pixels[x, y]
                target_pixels[x, y] = (r, g, b, new_alpha)

        target_img.save(target_path)
        return True
    except Exception as e:
        print(f"  Error processing {mask_path.name} -> {src_path.name}: {e}")
        return False


def main():
    work_dir = Path.cwd()

    # Find all xxx_.png files (mask files)
    mask_files = sorted(work_dir.glob("*_.png"))

    if not mask_files:
        print("No mask files (*_.png) found in current directory.")
        return

    processed = 0
    skipped = 0
    errors = 0

    for mask_path in mask_files:
        # xxx_.png -> xxx.png
        src_name = mask_path.stem[:-1] + ".jpg"  # remove trailing '_'
        src_path = mask_path.with_name(src_name)
        target_name = mask_path.stem[:-1] + ".png"  # remove trailing '_'
        target_path = mask_path.with_name(target_name)

        if not src_path.exists():
            print(f"  Skip: {mask_path.name} -> {target_name} not found")
            skipped += 1
            continue

        print(f"  Applying: {mask_path.name} -> {target_name}")
        if apply_alpha_mask(mask_path,src_path, target_path):
            processed += 1
        else:
            errors += 1

    print(f"\nDone: {processed} processed, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    main()
