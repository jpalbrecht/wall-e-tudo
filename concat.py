"""
concat_random.py

For every audio file X in voice_dir, randomly pick two audio files A,B from r2d2_dir,
create A + X + B and save into out_dir.

Dependencies:
  pip install pydub
  ffmpeg must be installed and available on PATH (or configure pydub.AudioSegment.converter)

Usage:
  python concat_random.py \
    --voice_dir ./voice_gladios_pitched \
    --r2d2_dir ./r2d2_samples \
    --out_dir ./output_mixed \
    --format ogg \
    --seed 123

Notes:
  - By default exports as WAV to avoid codec/ffmpeg parameter issues.
  - If r2d2_dir has fewer than 2 files the script will allow repetition.
  - Supported input file types depend on your ffmpeg build (mp3, wav, flac, m4a, ogg, etc).
"""

import argparse
import random
import sys
import os
from pathlib import Path
from pydub import AudioSegment

AUDIO_EXTS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".aiff", ".aif"}

def list_audio_files(dirpath):
    p = Path(dirpath)
    if not p.exists():
        return []
    return [f for f in sorted(p.iterdir()) if f.is_file() and f.suffix.lower() in AUDIO_EXTS]

def make_safe_filename(s: str) -> str:
    # Replace spaces and problematic chars
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in s)

def main(voice_dir, r2d2_dir, out_dir, out_format, seed, allow_same):
    voice_files = list_audio_files(voice_dir)
    cute_files = list_audio_files(r2d2_dir)

    if not voice_files:
        print(f"ERROR: no audio files found in voice_dir: {voice_dir}", file=sys.stderr)
        sys.exit(1)
    if not cute_files:
        print(f"ERROR: no audio files found in r2d2_dir: {r2d2_dir}", file=sys.stderr)
        sys.exit(1)

    random.seed(seed)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"Found {len(voice_files)} voice files and {len(cute_files)} cute files.")
    print("Processing...")

    for vf in voice_files:
        # choose A and B
        if len(cute_files) >= 2:
            A, B = random.sample(cute_files, 2)
        else:
            # only one cute file: allow repetition (or changed by allow_same flag)
            if allow_same:
                A = B = cute_files[0]
            else:
                # choose A = that file, B = same file (no choice available)
                A = B = cute_files[0]

        try:
            # load segments with pydub (ffmpeg backend)
            segA = AudioSegment.from_file(A)
            segX = AudioSegment.from_file(vf)
            segB = AudioSegment.from_file(B)

            # Optionally, normalize or match sample rates / channels:
            # pydub handles resampling when exporting, but to avoid glitches,
            # we'll convert everything to the same frame_rate & channels as segX:
            target_frame_rate = segX.frame_rate
            target_channels = segX.channels
            target_sample_width = segX.sample_width

            if segA.frame_rate != target_frame_rate:
                segA = segA.set_frame_rate(target_frame_rate)
            if segB.frame_rate != target_frame_rate:
                segB = segB.set_frame_rate(target_frame_rate)
            if segA.channels != target_channels:
                segA = segA.set_channels(target_channels)
            if segB.channels != target_channels:
                segB = segB.set_channels(target_channels)
            if segA.sample_width != target_sample_width:
                segA = segA.set_sample_width(target_sample_width)
            if segB.sample_width != target_sample_width:
                segB = segB.set_sample_width(target_sample_width)

            # Concatenate: A + X + B
            out_seg = segA + segX + segB

            # Build output filename
            base_vname = vf.stem
            base_A = A.stem
            base_B = B.stem
            safe_name = make_safe_filename(f"{base_vname}__A-{base_A}__B-{base_B}")
            outfile = out_path / f"{base_vname}.{out_format}"

            # Export
            out_seg.export(outfile.as_posix(), format=out_format)
            print(f"Saved: {outfile}  (A={A.name}, X={vf.name}, B={B.name})")
        except Exception as e:
            print(f"ERROR processing {vf}: {e}", file=sys.stderr)

    print("Done.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="For each voice file X, create A+X+B from random A,B in r2d2_dir.")
    parser.add_argument("--voice_dir", required=True, help="Directory containing voice_gladios_pitched files")
    parser.add_argument("--r2d2_dir", required=True, help="Directory containing r2d2 sound files")
    parser.add_argument("--out_dir", required=True, help="Directory to save concatenated outputs")
    parser.add_argument("--format", default="ogg", choices=["wav","mp3","flac","ogg","m4a"], help="Output audio format")
    parser.add_argument("--seed", type=int, default=None, help="Random seed (for reproducible sampling)")
    parser.add_argument("--allow_same", action="store_true", help="Allow A and B to be the same file even when more than 1 file exists")
    args = parser.parse_args()

    if args.allow_same:
        # If they explicitly allow same, we still sample without replacement when there are >=2 files,
        # unless we want to let sample choose duplicates — user explicitly asked for two tracks, so default is without replacement.
        pass

    main(args.voice_dir, args.r2d2_dir, args.out_dir, args.format, args.seed, args.allow_same)
