## Business Goal

Generate a concept image of Jolly in Visual Novel in the style of a PC-98 game.

## Technical Uncertainty
- How well will Meta Muse Image 1.0 handle UIs, especially in a particular style.

## Technical Configuration
- I'm just going to ask Meta Muse Code to generate image the iamge.

## Technical Exploration
- Reused `find-jolley-assets/src/generate_jolly_sheet.py` (Muse Image 1.0 via Responses API) with `--reference-image find-jolley-assets/outputs/jolly-character-sheet-v4.webp` to keep Jolly on-model.
- Prompt in `stylized-pc98-jolly-visual-novel-concept/pc98-jolly-vn-prompt.txt`: night school courtyard, centered Jolly sprite with orb, PC-98 UI (top status bar + bottom dialogue box with JOLLY name plate).
- Note: script's `load_dotenv()` only sees `.env` in cwd, so ran from repo root with `set -a; . find-jolley-assets/.env; set +a` prefix.
- Output: `stylized-pc98-jolly-visual-novel-concept/outputs/pc98-jolly-vn-v1.webp` (resp_6ac7ebd21e3c393111b54aa8).
- So the first type was okay, but I would describe it looking more like A JRPG rather than a visual novel. I have grabbed source example iamges from real PC-98 titles to see if that helps
- v2 diagnosis from the three source shots (CAL-style): real PC-98 VN grammar = LARGE waist-up portrait cropped by frame, full-width bottom box, decorative side borders, NO top status bar. v1's JRPG tells were the small centered sprite + status bar + English name plate.
- v2 prompt (`pc98-jolly-vn-prompt-v2.txt`) assigns roles explicitly: Jolly v4 sheet = character, `sources/cal-ii_5.png` + `sources/3548c849-8db9-40e3-a7c9-d09f59b2682c.png` = layout/UI only (skipped `cal_7.jpg`, heavy JPEG artifacts). All three fed via `--reference-image`.
- Output: `outputs/pc98-jolly-vn-v2.webp` (resp_6ac7ed890eff8604a7024611). Result: large Jolly portrait left holding orb toward viewer, navy full-width box with two legible Japanese lines + red ▼ marker, filigree side borders, courtyard background. No human-girl bleed. Genuine VN read this time.
- We have better generated image, but it did wholesale copy the detailing for the sidebars. It should have invented it own, but lets take direction.
- ChatGPT using GPT 2.5 image created a very good single concept, but I dont know if Muse 1.0 can produce something similar, it might be due to our generated image prompt, lets focus on just that GPT 2.5 image and see what Muse can come out with on the other end.
- v3: single-reference test, GPT image only (`sources/gpt-25-_jolly___s_cozy_pc-98_morning.png`), no CAL refs, no char sheet. Prompt (`pc98-jolly-vn-prompt-v3.txt`) mirrors the reference composition + exact menu/dialogue strings.
- Output: `outputs/pc98-jolly-vn-v3.webp` (resp_6ac7eedb94888cc0cba1486a). Verdict: yes, Muse 1.0 can match it — same cozy-room composition, all six menu items + dialogue legible, pink-trim UI, Jolly on-model with heavier PC-98 dithering than the GPT original. So the v2 gap was prompt/reference scope, not a model ceiling.
- Scenes batch (`scenes-manifest.md`): five new scenes generated from golden v3 as the sole reference into `outputs/scenes/` (s01 matsuri resp_6ac7f1532300e3cc57c84041, s02 shrine resp_6ac7f1748ec8652a731f4a99, s03 rooftop resp_6ac7f19227733e3ee1cf4595, s04 ramen resp_6ac7f1aaf584c69128b04abe, s05 lake resp_6ac7f1ca65353812dfbe401c). All five hold style, UI grammar and legible Japanese; s02 is cleanest. Known drifts: s01 Jolly gains eyebrows + open smile, background signage stays decorative gibberish. Mirrored right-side portrait (s04) and narration-only box (s02) both work, so the recipe generalizes across layouts.
- Anchored v2 wave: brought the generator in-house as `src/generate_scenes.py` (adapted from `find-jolley-assets`, anchors from local `references/`, per-scene prompts unchanged in intent). All five scenes ran as one chained conversation with the character sheet + style reference attached on every turn. Result in `outputs/scenes/v2/` (v1 moved to `outputs/scenes/v1/`): eyebrows gone everywhere and 4/5 fully on-model; only s01 keeps the open-mouth smile, which reads as the scene prompt's "delighted" wording beating the anchor. Lesson: emotion words in a scene prompt can override a neutral anchor, so keep expression language out of scene beats unless the beat needs it.
- Before wrapping up I asked Muse Code to make a manifest file and generate 5 other scenes in a the outputs/scenes directory but we have some inconsisteny with the character. Maybe its not feeding in the refernece sheet each time.
## Technical Goal
Screenshot-style concept image: Jolly as a PC-98 visual novel sprite with authentic HUD.

## Technical Conclusion
Muse Image 1.0 can render UI-heavy period style convincingly, since all three runs produced legible Japanese text and coherent layouts. The quality of the result depends on the scope of the references rather than the capability of the model, because loose prompts drift into adjacent genres while loose reference sets import details that were never requested.

The first attempt used only the Jolly character sheet as reference, which kept the character on-model and produced a legible status bar, although the composition came out as a JRPG battle screen because nothing in the prompt described visual-novel grammar. The second attempt added two genuine PC-98 screenshots, and whereas the layout became correct (large cropped portrait, full-width dialogue box, decorative side borders, no human bleed), the model copied the CAL sidebar filigree wholesale instead of inventing ornament of its own. The third attempt therefore used the single GPT concept image as the sole reference with a prompt that mirrored its composition and quoted its exact menu and dialogue strings, which produced a near one-to-one recreation with even heavier authentic dithering than the original.

The working recipe is one reference image per role, exact UI strings in the prompt, and explicit exclusions for elements the genre does not use. The remaining weakness is minor glyph wobble in small or icon-slot text, which stayed within acceptable bounds on every run.

We generated out multiple scenes and the uncovered consistency issues.
We did improve with a golden reference image for character and visual style UI.
Its consisteny is better, but we still have some issues, like with fur, and ahereing to style.