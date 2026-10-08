# Jolly — Normalized Character Sheet Image Prompt

Source analysis from `find-jolley-assets/sources/` (5 images reviewed 2026-10-08).
Best reference: `mashable-jolly-hero.jpg` (clean close-up, default Jolly + orb).

## Consistent traits observed
- Small chubby rounded pill / yeti-like mascot, ~2 heads tall, super-deformed kawaii 3D render.
- Full-body short plush fur suit in warm off-white / cream (#F3ECE1), face opening shows smooth matte cream face disk (#FDF3E7).
- Face: two small solid black glossy round eyes, wide-set; tiny simple closed-mouth curved smile, centered; soft pink blush on both cheeks.
- No nose, no ears, no fingers; stubby integrated arms with rounded paws, short stubby legs/feet.
- Optional signature prop: translucent iridescent blue-white glass orb with inner swirl/galaxy, held with both paws at chest.
- Variants to ignore for default: red flannel shirt (`zuck-muse-charm-getty.jpg`), open-mouth smile, plush-toy fuzz vs 3D render, holiday staging.

## Copy-paste image generation prompt

```
character reference sheet of Jolly, Meta Muse's mascot, default design, single character shown 4 times on one seamless plain white background: front view, side view, back view, three-quarter view, consistent design across all views, small chubby rounded pill-shaped yeti-like creature in warm off-white cream short plush fur, smooth matte cream oval face, two small solid black glossy round eyes wide-set, tiny simple curved closed-mouth smile, soft pink blush cheeks, no nose no ears, stubby integrated arms with rounded paws, short stubby legs, holding a small translucent iridescent blue-white glass orb with inner swirl at chest in front view only, soft studio lighting, Pixar-style 3D render, kawaii minimal, ultra-clean, high detail fur texture, neutral expression, character sheet layout, orthographic, full body visible, centered
```

## Negative prompt

```
no humans, no Mark Zuckerberg, no text, no logo, no watermark, no Muse logo, no clothes, no flannel, no costumes, no extra characters, no Duolingo owl, no background scene, no Christmas, no gifts, no device, no phone, no blur, no photo-of-screen, no cropped limbs, no scary, no realistic monster
```

## Tips
- Use 16:9 or square, high resolution.
- If model supports image reference, attach `mashable-jolly-hero.jpg` as style/character reference with low variance.
- Generate without orb first if hands merge into orb, then add orb as prop edit.
