## Business Goal

I want to create a bunch of AI driven projects based around Jolly, Meta Muse's mascot.
I need source images of Jolly, Can you help me find them?

## Technical Uncertainty

- Can Meta's model find my source images of Jolly on the internet?
- Can we use Meta's Image Model to create a normalized reference image?

## Technical Configuration
Mostly using 1.3 Spark on High for prompting
Muse Image for 1.0

## Technical Exploration
- Meta Muse Code is very literal, if you mispell your source folder it won't reason that very similar named one exists eg source vs sources
- It would be nice if Meta Dev API had expiring API keys.
- Meta Muse Code, ran my script that executed API models eg. Meta Muse Model without my permission first.

## Technical Goal

Create a solid reference image of Jolly for future use in our AI workloads.

## Technical Conclusion

I was able to use Meta Muse Code to create a script, with versioned prompts. It did reason well on how to generate the next iterations, It's image judgement was not as sharp, we did get a good enough character reference but I would have preferred a less chibi style image. V4 will be our chosen image going forward.

## Open Questions / Future Experiments
- Is it better to have a reference sheet of indivuaal images of profiles eg. front.jpg, side.jpg or just a single image sheet.
- Does having the text in the single reference sheet help or matter?