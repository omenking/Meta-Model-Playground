# Clean-asset generation prompts (no baked UI)

The 001 wave prompts asked the image model to draw the finished
screenshot (dialogue box, name plate, choice list, Jolly portrait).
That bakes engine UI into art. For the real game, generate layers:

## Backgrounds (scene only)

"Background art only, full frame, no characters, no people, no
text, no letters, no signs with words, no UI, no dialogue box, no
borders: <scene description>. Early-90s 2D anime background,
NEC PC-9801 palette, heavy dithering, 640x400 composition."

Scenes: matsuri street at night (lanterns, fireworks, stalls);
hillside shrine at dusk in snow; school rooftop at sunset; ramen
shop counter at night; mountain lake dock in morning mist.

## Jolly sprite (separate)

"Single character on a solid pure-magenta background, full body,
front view: small chubby cream-furred yeti-like mascot, round
black eyes, pink blush, gentle closed-mouth smile, no eyebrows,
no open mouth, stubby limbs, holding a glowing translucent
blue-white orb. No text, no UI." Chroma-key magenta to alpha,
crop, quantize last (key before quantizing or edges fringe).

## Rule

Anything the engine can draw (message box, name plate, choices,
chapter cards) must never be requested in image prompts.
