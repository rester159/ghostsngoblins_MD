# Help me finish Maximo's sprites! (community pixel-art call)

Hi everyone!

I'm working on a **Mega Drive / Genesis Ghosts 'n Goblins hack that replaces Arthur with Maximo**. The engine side is working, and Maximo is already in the game: he has his armor, his red cape and boxers, and a new face. But he started life as Arthur's frames run through a script, and **74 hand-sized frames need a human touch**. That's where you come in.

I made a small browser tool that does all the technical work for you. You only draw, and you can watch your frames animate exactly the way the game plays them.

## What you'll be doing

Cleaning up, improving, or completely redrawing Maximo's sprite frames, pixel by pixel:

- fixing the cape where the script made it blocky or odd-looking
- making the face read as Maximo, not "Arthur without a beard"
- cleaning stray pixels, outlines and shading
- making the boxer frames (armor knocked off) look like Maximo, not Arthur
- or, if you're feeling brave, **starting from a blank sheet** and drawing your own Maximo

## The rules (the tool enforces them, so you can't break anything)

The Mega Drive is strict, so the editor is too:

1. **Every frame is a fixed 32×32 box.** You can draw anywhere inside it: make the cape bigger, change the pose, add detail. The tool won't let you paint outside the box (the hatched area) because the hardware sprite can't hold those pixels.
2. **You can only use the 16 colors in the palette.** No color picker and no custom colors. Those 16 are exactly what the game has loaded for this character, so whatever you draw shows up in-game as it looks in the editor.
3. **Color 0 is transparent** (the checkerboard). Use it to erase.

## How to use the editor

**[Open the Maximo Pixel Editor](LINK-HERE)** in your browser (desktop works best). It runs in the browser, so there's nothing to install. If the embedded version gives you trouble, click fullscreen, or download the zip and open `index.html`.

### Pick your starting point

Click **New sheet…** and choose:

- **Start from Maximo**: the current Maximo conversion. Best for clean-up and polish. This is the default.
- **Start from Arthur**: the original Arthur frames from the game.
- **Blank sheet**: every frame empty, to draw from scratch.

You can also mix and match frame by frame. For any frame, **Import Arthur's frame** or **Import Maximo's frame** copies that version into your sheet. The **Overlay** menu shows Arthur or Maximo faintly under your pixels as a tracing guide (hold `O` to see it fully).

### The screen

- **Left side:** all the frames. Click one to edit it. Three are marked like "A5 = A3": the game reuses A3's slot for them, so you edit A3 and they follow. Frames you've changed get an orange dot. Hover a frame to see which animations use it.
- **Middle:** the big zoomed canvas. The orange border is the 32×32 limit, and the faint lines mark the 8×8 hardware tiles.
- **Right side:**
  - the locked palette
  - the current frame as Arthur, as Maximo and as yours, side by side
  - the **animation tester**

### Test your animations

Every move was recorded from the real game at its real speed (60 fps), so the tester shows exactly what players will see: idle, walking, crouching, jumping, jump-forward, throwing (standing, crouching and in the air), climbing ladders, getting the armor knocked off, and dying. Each one comes armored and in boxers, facing left and right.

- Pick a move from the list (or use `↑`/`↓`). It plays **your** frames, with Arthur's version next to them for comparison.
- Your edits show up in the animation immediately.
- Pause and step through it with `,` and `.`, at ½× or ¼× speed if you like.
- **Click the playing animation** to jump straight to the frame being shown.
- Frames used by the selected animation are highlighted in the frame list.

Note that left-facing poses are their own frames (the game doesn't mirror sprites), so remember to update both directions!

### Controls

| Action | How |
|---|---|
| Paint | Left-click / drag |
| Pick a color from the sprite | Right-click |
| Choose color | Click a swatch, or press `0`–`9`, `A`–`F` |
| Pencil / Fill / Eyedropper | `B` / `G` / `I` |
| Undo / Redo | `Ctrl/Cmd+Z` / `Ctrl/Cmd+Shift+Z` |
| Previous / next frame | `←` / `→` |
| Previous / next animation | `↑` / `↓` |
| Play / pause animation | `Space` |
| See the overlay fully | Hold `O` |

Your work **autosaves in your browser**, so you can close the tab and come back. It's still a good idea to export now and then.

## How to send me your work

1. **Claim your frames first.** Post a comment like *"Claiming the left-facing walk, B31–B34"* (frame names are shown on each thumbnail) so two people don't redo the same frames. Check the comments to see what's taken. Claiming a whole animation is a great way to keep it consistent.
2. Draw, and check it in the animation tester!
3. Click **Export banks**. You'll get three files: `maximo_bankA.bin`, `maximo_bankB.bin` and `maximo_bankC.bin`.
4. Upload **all three files** (zip them if that's easier) in a comment, or send them to me via LINK/EMAIL/DISCORD.
5. Optional but appreciated: click **Export PNG sheet** and post the image so everyone can see your work.

Don't worry about the parts you didn't touch. I merge only the frames you actually changed, so several people can work on different frames at once.

To continue someone else's work, or your own from another computer, use **Load .bin…** and pick all three files.

## Tips

- Turn the grid off (`H`) and watch the animation tester often. Pixel art that looks great zoomed in can turn to mush at real size, and a frame that looks fine alone can pop in motion.
- Keep the cape and face consistent across a whole animation.
- Stick to the existing light sources and outline style so your frames blend in with everyone else's.
- Faded thumbnails are frames I didn't see in any recorded move. They're low priority.
- The last frame, **C0**, is Maximo raising his fist on the screen between stages. It isn't in the animation tester, but it's worth some love: no helmet, so the face and hair really show.

## Credits

Everyone whose frames make it into the release will be credited in the readme and on this page. Tell me the name you'd like to be credited as.

Thanks so much! I can't wait to see what you come up with. ❤️
