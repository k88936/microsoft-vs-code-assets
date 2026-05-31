#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Extract zombie variant animations from Zombie.reanim.xml.

Reads Zombie.reanim.xml (the master animation file with <root> wrapper)
and generates one .reanim file per variant definition.

Each variant can include multiple animation tracks and optionally exclude
specific base or body-part tracks (e.g., screendoor variant replaces
outerarm body tracks with screendoor-specific arm tracks).

Usage:
    uv run extract_variants.py [--dry-run] [--source PATH]
"""

import argparse
import os
import re
import sys

# Behavior animation tracks common to all zombie variants.
# Previously standalone variant tracks anim_innerarm1/2/3 are now base tracks.
BASE_ANIMS = [
    "anim_superlongdeath",
    "anim_death2",
    "anim_death",
    "anim_walk2",
    "anim_walk",
    "anim_idle2",
    "anim_idle",
    "anim_eat",
    "anim_dance",
]

VARIANTS = [
    {
        "includes": [
            "anim_duckytube",
            "anim_whitewater",
        ],
        "excludes": [
            "Zombie_innerleg_upper",
            "Zombie_outerleg_upper",
            "Zombie_innerleg_lower",
            "Zombie_outerleg_lower",
            "Zombie_innerleg_foot",
            "Zombie_outerleg_foot",
        ],
        "include_anims":[
            "anim_swim",
            "anim_waterdeath",
        ],
        "exclude_anims":[
            "anim_walk2",
            "anim_walk",
            "anim_superlongdeath",
            "anim_death2",
            "anim_death",
            "anim_dance",
        ]
    },
    "anim_mustache",
    {
        "includes": [
            "anim_screendoor",
            "anim_innerarm_screendoor_hand",
            "anim_innerarm_screendoor",
            "anim_outerarm_screendoor",
        ],
        "excludes": [
            "Zombie_outerarm_hand",
            "Zombie_outerarm_upper",
            "Zombie_outerarm_lower",
            "Zombie_innerarm1",
            "Zombie_innerarm2",
            "Zombie_innerarm3",
        ],
    },
    {
        "includes": ["anim_flaghand", ],
        "excludes": [
            "Zombie_innerarm1",
            "Zombie_innerarm2",
            "Zombie_innerarm3",
        ]
    },

    "anim_cone",
    "anim_bucket",
]

NAME_RE = re.compile(r"<name>(.*?)</name>")


def parse_tracks(source_path: str):
    """Parse Zombie.reanim.xml and return fps + all tracks.

    Handles the <root> wrapper and 4-space indentation.
    Strips indentation from lines so output is flat (no indentation).

    Returns (fps_value, all_tracks) where all_tracks is a list of
    (name_or_None, full_track_text) tuples in file order.
    """
    all_tracks: list[tuple[str | None, str]] = []
    fps_value: str | None = None
    in_track = False
    track_lines: list[str] = []

    with open(source_path, "r") as f:
        for line in f:
            stripped = line.strip()

            # --- Capture fps ---
            if fps_value is None:
                fps_match = re.match(r"<fps>(\d+)</fps>", stripped)
                if fps_match:
                    fps_value = fps_match.group(1)
                    continue

            # --- Skip root wrapper / blank lines ---
            if not in_track:
                if stripped == "<track>":
                    in_track = True
                    track_lines = ["<track>"]
                # Lines outside <track> (e.g., <root>, </root>, blank) are skipped
            else:
                track_lines.append(stripped)
                if stripped == "</track>":
                    in_track = False
                    full_track = "\n".join(track_lines) + "\n"
                    name_match = NAME_RE.search(full_track)
                    name = name_match.group(1) if name_match else None
                    all_tracks.append((name, full_track))

    if fps_value is None:
        sys.exit("Error: Could not find <fps> tag in source file")

    return fps_value, all_tracks


def get_output_filename(first_include: str) -> str:
    """Convert e.g. 'anim_bucket' to 'Zombie_bucket.reanim'."""
    suffix = first_include.removeprefix("anim_")
    return f"Zombie_{suffix}.reanim"


def resolve_variant(variant_def):
    """Normalize a variant definition into (includes, excludes, include_anims, exclude_anims, suffix)."""
    if isinstance(variant_def, str):
        return [variant_def], [], [], [], variant_def.removeprefix("anim_")
    includes = variant_def.get("includes", [])
    excludes = variant_def.get("excludes", [])
    include_anims = variant_def.get("include_anims", [])
    exclude_anims = variant_def.get("exclude_anims", [])
    suffix = includes[0].removeprefix("anim_") if includes else ""
    return includes, excludes, include_anims, exclude_anims, suffix


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract zombie variant animations from Zombie.reanim.xml"
    )
    parser.add_argument(
        "--source",
        default="Zombie.reanim.xml",
        help="Path to the master file (default: Zombie.reanim.xml)",
    )
    args = parser.parse_args()

    source_path = args.source

    if not os.path.exists(source_path):
        sys.exit(f"Error: source file not found: {source_path}")

    fps_value, all_tracks = parse_tracks(source_path)

    print(f"Parsed {source_path}")
    print(f"  Total tracks:        {len(all_tracks)}")
    print(f"  fps:                 {fps_value}")
    print(f"  Variant definitions: {len(VARIANTS)}")
    print()

    # Non-anim tracks are all tracks whose name does NOT start with "anim_".
    # Per the formula: final = BASE_ANIMS + BASIC_TRACKS + includes - excludes
    # where BASIC_TRACKS = tracks with name not starting with "anim_".

    out_dir = os.path.dirname(source_path) or "."
    for v in VARIANTS:
        includes, excludes, include_anims, exclude_anims, suffix = resolve_variant(v)
        out_name = f"Zombie_{suffix}.reanim"
        out_path = os.path.join(out_dir, out_name)

        exclude_set = set(excludes) | set(exclude_anims)
        include_set = set(includes)
        include_anims_set = set(include_anims)

        with open(out_path, "w") as f:
            # 1) fps header
            f.write(f"<fps>{fps_value}</fps>\n")

            # 2) All tracks in source file order — single pass preserves interleaving
            for name, track in all_tracks:
                if name is None:
                    f.write(track)
                    continue

                # Skip explicitly excluded tracks (includes exclude_anims)
                if name in exclude_set:
                    continue

                # Base anim tracks + per-variant include_anims
                if name in BASE_ANIMS or name in include_anims_set:
                    f.write(track)
                    continue

                # Variant include tracks for THIS variant (rename anim_* → Zombie_*)
                if name in include_set:
                    new_name = name.replace("anim_", "Zombie_", 1)
                    renamed_track = track.replace(
                        f"<name>{name}</name>", f"<name>{new_name}</name>", 1
                    )
                    f.write(renamed_track)
                    continue

                # Non-anim tracks: names not starting with "anim_" — BASIC_TRACKS
                if not name.startswith("anim_"):
                    f.write(track)
                    continue

                # anim_* tracks not in BASE_ANIMS, not in include_anims, and not in
                # this variant's includes → skip (belong to other variants)
                continue

        print(f"Generated: {out_path}")

    print(f"\nDone. Generated {len(VARIANTS)} files.")


if __name__ == "__main__":
    main()
