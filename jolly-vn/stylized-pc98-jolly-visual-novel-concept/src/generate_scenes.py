"""Anchored wave generator for Jolly PC-98 visual-novel scenes.

Follows the anchored-generation recipe (fix the recurring subjects once,
then chain every later turn from them with ``previous_response_id``): the
Jolly character sheet and the golden PC-98 style reference are attached as
``input_image`` anchors on every turn, and each scene after the first also
chains from the previous turn's response id, so the conversation carries the
locked character and UI language forward without re-description.

Adapted from ``find-jolley-assets/src/generate_jolly_sheet.py``: the client,
API key handling, and image-saving helpers use the same Responses-API
pattern (``muse-image-1.0``, base64 image on the ``image_generation_call``
item). The v1 scenes were one-shot calls (style reference only, fresh
conversation each time), which is why Jolly drifted; this script fixes both
gaps at once.

Usage (from the repository root):
  <venv>/bin/python stylized-pc98-jolly-visual-novel-concept/src/generate_scenes.py --dry-run
  <venv>/bin/python stylized-pc98-jolly-visual-novel-concept/src/generate_scenes.py --force

The API key comes from ``MODEL_API_KEY`` (or ``MUSE_SPARK_API_KEY``): the
environment first, then ``.env`` in the working directory, then
``find-jolley-assets/.env``. Every run appends ``{prompt, out,
response_id}`` lines to ``run-log.jsonl`` in the output directory, so a wave
is resumable and auditable.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

HERE = Path(__file__).resolve()
CONCEPT_ROOT = HERE.parent.parent  # stylized-pc98-jolly-visual-novel-concept/
REPO_ROOT = CONCEPT_ROOT.parent

MODEL_DEFAULT = "muse-image-1.0"

DEFAULT_ANCHORS = [
    CONCEPT_ROOT / "references" / "jolly-character-sheet.webp",
    CONCEPT_ROOT / "references" / "pc98-jolly-vn-style.webp",
]

# Names the attached anchors in order; prepended to every scene prompt so the
# model cannot mistake the style reference's composition for the assignment.
ANCHOR_PREAMBLE = (
    "ANCHORS (two attached images, in order). "
    "(1) Jolly character reference sheet: the ONLY definition of Jolly — "
    "small chubby cream-furred yeti-like mascot, round black eyes, pink "
    "blush, gentle closed-mouth smile, no eyebrows, no open mouth, stubby "
    "limbs. Render Jolly EXACTLY per this sheet in every scene. "
    "(2) Golden PC-98 screenshot: defines rendering only (NEC PC-9801, "
    "640x400, 16 colors, heavy dithering, scanlines, 4:3) and UI language "
    "(black dialogue box, pink trim, corner ornaments, pixel Japanese text, "
    "pink markers). Match its style and UI, never its morning-room scene. "
    "New scene below."
)


def build_client() -> OpenAI:
    """Build an OpenAI-compatible client; fall back to the sibling .env."""
    load_dotenv()
    if not (os.getenv("MODEL_API_KEY") or os.getenv("MUSE_SPARK_API_KEY")):
        sibling = REPO_ROOT / "find-jolley-assets" / ".env"
        if sibling.exists():
            load_dotenv(sibling)
    api_key = os.getenv("MODEL_API_KEY") or os.getenv("MUSE_SPARK_API_KEY")
    if not api_key:
        raise RuntimeError("Missing API key: export MODEL_API_KEY first.")
    base_url = os.getenv("MUSE_SPARK_BASE_URL") or "https://api.meta.ai/v1"
    return OpenAI(api_key=api_key, base_url=base_url)


def image_data_url(path: Path) -> str:
    """Read a local image and return it as a base64 data URL."""
    mime, _ = mimetypes.guess_type(path.name)
    raw = path.read_bytes()
    return f"data:{mime or 'application/octet-stream'};base64," + base64.b64encode(
        raw
    ).decode()


def build_input(scene_text: str, anchors: list[Path]):
    """Preamble + scene text, followed by the anchor images in order."""
    content: list[dict] = [
        {"type": "input_text", "text": f"{ANCHOR_PREAMBLE}\n\n{scene_text.strip()}"}
    ]
    for anchor in anchors:
        content.append({"type": "input_image", "image_url": image_data_url(anchor)})
    return [{"role": "user", "content": content}]


def save_image_result(response, out_path: Path) -> Path:
    """Pull the base64 image out of a Responses output list and write it."""
    try:
        b64 = next(
            item.result
            for item in response.output
            if item.type == "image_generation_call"
        )
    except StopIteration:
        raise RuntimeError(
            f"No image in response (status={response.status})."
        ) from None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(base64.b64decode(b64))
    return out_path


def default_prompts() -> list[Path]:
    """The five wave scene prompts, in scene order."""
    return sorted(CONCEPT_ROOT.glob("pc98-jolly-vn-s0*.txt"))


def scene_out(prompt_path: Path, out_dir: Path) -> Path:
    """Map pc98-jolly-vn-s01-matsuri.txt -> <out_dir>/pc98-jolly-vn-s01-matsuri.webp."""
    return out_dir / (prompt_path.stem + ".webp")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate an anchored wave of Jolly PC-98 scenes."
    )
    parser.add_argument(
        "--prompt",
        action="append",
        default=None,
        metavar="PATH",
        help="Scene prompt file; repeat per scene. Default: all s0*.txt in order.",
    )
    parser.add_argument(
        "--anchor",
        action="append",
        default=None,
        metavar="PATH",
        help="Anchor image, attached in order. Default: character sheet + style.",
    )
    parser.add_argument(
        "--out-dir",
        default=str(CONCEPT_ROOT / "outputs" / "scenes" / "v2"),
        help="Where to save the wave.",
    )
    parser.add_argument("--model", default=MODEL_DEFAULT)
    parser.add_argument(
        "--no-chain",
        action="store_true",
        help="Do not pass previous_response_id between scenes (independent turns).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing output files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the chained plan without calling the API.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    prompts = [Path(p) for p in args.prompt] if args.prompt else default_prompts()
    if not prompts:
        raise RuntimeError("No scene prompts found.")
    anchors = [Path(a) for a in args.anchor] if args.anchor else list(DEFAULT_ANCHORS)
    for anchor in anchors:
        if not anchor.exists():
            raise RuntimeError(f"Missing anchor image: {anchor}")
    out_dir = Path(args.out_dir)
    outs = [scene_out(p, out_dir) for p in prompts]
    if not args.force:
        for out in outs:
            if out.exists():
                raise RuntimeError(
                    f"Refusing to overwrite existing file: {out} (pass --force)."
                )
    log_path = out_dir / "run-log.jsonl"
    if args.dry_run:
        print(f"model: {args.model}")
        print(f"anchors: {[str(a) for a in anchors]}")
        print(f"chained: {not args.no_chain}")
        for prompt, out in zip(prompts, outs):
            print(f"  {prompt.name} -> {out}")
        print(f"run log: {log_path}")
        return 0
    client = build_client()
    prev_id: str | None = None
    for prompt, out in zip(prompts, outs):
        scene_text = prompt.read_text(encoding="utf-8")
        kwargs: dict = {
            "model": args.model,
            "input": build_input(scene_text, anchors),
        }
        if prev_id and not args.no_chain:
            kwargs["previous_response_id"] = prev_id
        response = client.responses.create(**kwargs)
        saved = save_image_result(response, out)
        prev_id = response.id
        with log_path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {"prompt": str(prompt), "out": str(saved), "response_id": prev_id}
                )
                + "\n"
            )
        print(f"Saved: {saved}")
        print(f"response id: {prev_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
