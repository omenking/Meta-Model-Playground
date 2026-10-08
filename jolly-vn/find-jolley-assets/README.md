# Jolly character sheet generator

`src/generate_jolly_sheet.py` sends the prompt in `src/jolly-character-sheet-prompt.txt`
to `muse-image-1.0` through the OpenAI SDK's Responses API and saves the resulting
reference sheet to `outputs/jolly-character-sheet.webp`. Because the prompt lives in
its own text file, you can revise the character description without editing any code,
and the `--prompt-file` flag selects an alternate prompt whenever you want to try a
variation. Note that `muse-spark-1.3` is a text model and cannot generate images, which
is why the script targets the Muse Image model instead.

To iterate, point `--reference-image` at the current sheet so the next render steers
from it, and pass `--previous-response-id` with the id the script printed to refine an
earlier turn instead of starting fresh. The script never overwrites an existing output
file unless you pass `--force`, so versioned runs land side by side by default.

Configuration comes from `find-jolley-assets/.env`, which already sets
`MUSE_SPARK_BASE_URL` to the standard Meta endpoint (`https://api.meta.ai/v1`),
so you only need to provide `MUSE_SPARK_API_KEY`. Dependencies are `openai` and
`python-dotenv`, as listed in `src/requirements.txt`. The environment lives in
`find-jolley-assets/.venv`, so a fresh shell needs only the activation step before
running the script. All commands below run from the repository root.

```bash
# One-time setup.
python3 -m venv find-jolley-assets/.venv
source find-jolley-assets/.venv/bin/activate
pip install -r find-jolley-assets/src/requirements.txt

# Preview the resolved model and prompt without calling the API.
python find-jolley-assets/src/generate_jolly_sheet.py --dry-run

# Generate the reference sheet.
python find-jolley-assets/src/generate_jolly_sheet.py

# Use a different prompt or output path.
python find-jolley-assets/src/generate_jolly_sheet.py \
  --prompt-file /tmp/my-prompt.txt \
  --out find-jolley-assets/outputs/jolly-variant.webp

# Iterate v2 from a new prompt, steered by the current sheet.
python find-jolley-assets/src/generate_jolly_sheet.py \
  --prompt-file find-jolley-assets/src/jolly-character-sheet-prompt-v2.txt \
  --reference-image find-jolley-assets/outputs/jolly-character-sheet.webp \
  --out find-jolley-assets/outputs/jolly-character-sheet-v2.webp
```
