# Jolly PC-98 VN — Scene Manifest

Wave v1 (one-shot calls, style reference only, fresh conversation each time)
lives in `outputs/scenes/v1/`. Wave v2 (anchored: character sheet + style
reference attached every turn, all five scenes chained in one conversation
via `previous_response_id`) lives in `outputs/scenes/v2/` with
`run-log.jsonl`. Scene 00 (`outputs/pc98-jolly-vn-v3.webp`) is the golden
style reference.

## Wave v1 — outputs/scenes/v1/ (superseded)
- s01 matsuri / s02 shrine / s03 rooftop / s04 ramen / s05 lake.
- Verdict: style and UI held, but Jolly drifted (eyebrows + open-mouth smile
  in s01). Cause: no character anchor, no chaining.

## Wave v2 — outputs/scenes/v2/ (current)
- Script: `src/generate_scenes.py` (anchors from `references/`).
- s01 matsuri (resp_6ac7f3d795fcaf1159d74e70): eyebrows gone, but the
  open-mouth smile persists — the scene prompt's "delighted" wording likely
  overrode the anchor. UI + both dialogue lines exact.
- s02 shrine (resp_6ac7f3ec4e2c606b25564577): fully on-model, narration box
  exact. Cleanest of the wave.
- s03 rooftop (resp_6ac7f40e022219f44c44413d): fully on-model, orb reflects
  the sunset, both lines exact.
- s04 ramen (resp_6ac7f42e01065ac1e1fc42e2): fully on-model, mirrored
  right-side portrait + shop menu + meal ticket all hold, both lines exact.
- s05 lake (resp_6ac7f44fed16e55d1ab04e1d): fully on-model, orb raised to
  the sun, both lines exact.
- Residual: background signage and wall slips stay decorative gibberish;
  small-text fidelity remains the weak axis, not the character.
