"""Generate Jolly character reference sheet via Muse Image (OpenAI SDK).

Uses the Responses API with the image model (default ``muse-image-1.0``):
each ``client.responses.create(...)`` call is one conversation turn, and the
rendered image comes back as base64 on the ``image_generation_call`` item.
``muse-spark-1.3`` is a text model and cannot serve image requests.
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

MODEL_DEFAULT = "muse-image-1.0"

# External prompt file kept next to this script; --prompt-file overrides it.
DEFAULT_PROMPT_FILE = Path(__file__).with_name("jolly-character-sheet-prompt.txt")


def build_client() -> OpenAI:
    """Build an OpenAI-compatible client from .env."""
    load_dotenv()
    api_key = (
        os.getenv("MODEL_API_KEY")
        or os.getenv("MUSE_SPARK_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    base_url = os.getenv("MUSE_SPARK_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    if not api_key:
        raise RuntimeError(
            "Missing API key: set MUSE_SPARK_API_KEY (or OPENAI_API_KEY) in .env"
        )
    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def resolve_prompt(args: argparse.Namespace) -> str:
    prompt_path = (
        Path(args.prompt_file) if args.prompt_file else DEFAULT_PROMPT_FILE
    )
    return prompt_path.read_text(encoding="utf-8").strip()


def image_data_url(path: str | Path) -> str:
    """Read a local image and return it as a base64 data URL."""
    path = Path(path)
    mime, _ = mimetypes.guess_type(path.name)
    raw = path.read_bytes()
    return f"data:{mime or 'application/octet-stream'};base64," + base64.b64encode(
        raw
    ).decode()


def build_input(prompt: str, reference_images: list[str] | None):
    """Build the Responses API input, attaching reference images if given."""
    if not reference_images:
        return prompt
    return [
        {
            "role": "user",
            "content": [{"type": "input_text", "text": prompt}]
            + [
                {"type": "input_image", "image_url": image_data_url(p)}
                for p in reference_images
            ],
        }
    ]


def ensure_out_available(out: str | Path, force: bool) -> Path:
    """Fail before any API call if the output file already exists."""
    out_path = Path(out)
    if out_path.exists() and not force:
        raise RuntimeError(
            f"Refusing to overwrite existing file: {out_path} "
            "(choose another --out or pass --force)."
        )
    return out_path


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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Jolly character sheet with Muse Image."
    )
    parser.add_argument(
        "--prompt-file",
        default=None,
        help="Path to a text file with the image prompt (default: jolly-character-sheet-prompt.txt).",
    )
    parser.add_argument(
        "--out",
        default="find-jolley-assets/outputs/jolly-character-sheet.webp",
        help="Where to save the generated image.",
    )
    parser.add_argument("--model", default=MODEL_DEFAULT)
    parser.add_argument(
        "--reference-image",
        action="append",
        default=None,
        metavar="PATH",
        help="Local image to steer the render; repeat for several. "
        "The current sheet works well here.",
    )
    parser.add_argument(
        "--previous-response-id",
        default=None,
        metavar="ID",
        help="Chain onto an earlier turn; the script prints each new "
        "response id for follow-up refinements.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting an existing --out file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved model/prompt without calling the API.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    prompt = resolve_prompt(args)
    out_path = ensure_out_available(args.out, args.force)
    if args.dry_run:
        print(f"model: {args.model}")
        print(f"out: {out_path}")
        print(f"reference images: {args.reference_image or 'none'}")
        print(f"previous response: {args.previous_response_id or 'none'}")
        print("prompt:")
        print(prompt)
        return 0
    client = build_client()
    kwargs = {"model": args.model, "input": build_input(prompt, args.reference_image)}
    if args.previous_response_id:
        kwargs["previous_response_id"] = args.previous_response_id
    response = client.responses.create(**kwargs)
    saved = save_image_result(response, out_path)
    print(f"Saved: {saved}")
    print(f"response id: {response.id} (pass as --previous-response-id to refine)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
