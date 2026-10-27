# Help me draw Firebrand! (community pixel-art call)

Hi everyone!

My **Mega Drive / Genesis Ghosts 'n Goblins hack** has a Firebrand campaign: you play as the Red Arremer himself, with hovering, fireballs and one-hit deaths. Firebrand is already in the game, built from his Demon's Crest sprites scaled down to Genesis size. That conversion was automatic, though, and **his frames need a human touch**. That's where you come in.

I made a small browser tool that does all the technical work for you. You only draw, and you can watch your frames animate exactly the way the game plays them.

## What you'll be doing

Improving, or completely redrawing, Firebrand's sprite frames, pixel by pixel:

- cleaning up the scaled-down Demon's Crest art (stray pixels, muddy shading, the head)
- making his walk and hover cycles read clearly at real size
- giving poses like crouch, throw (fire) and the ladder climb more personality
- drawing his **wall cling** (resting and firing), new with the Gargoyle's Quest-style wall grab
- or, if you're feeling brave, **starting from a blank sheet** and drawing your own Firebrand

## The rules (the tool enforces them, so you can't break anything)

1. **Every frame is a fixed 48×32 box**: a 32×32 body in the middle, plus an 8-pixel **wing column** on each side for spread wings. You can draw anywhere inside the box, but not outside it.
2. **Each frame uses one locked palette line.** Almost every frame uses **line 0**, the 15 colors shared by every player sprite. The burn-up (death) flames use **line 2**. The editor only offers the right colors for each frame, so you can't mix palettes, and whatever you draw shows up in-game as it looks in the editor.
3. **Color 0 is transparent** (the checkerboard). Use it to erase.

## How to use the editor

**[Open the Firebrand Pixel Editor](LINK-HERE)** in your browser (desktop works best). There's nothing to install. If the embedded version gives you trouble, click fullscreen, or download the zip and open `index.html`.

### Pick your starting point

Click **New sheet…** and choose:

- **Start from the in-game Firebrand**: what's in the game right now. Best for clean-up and polish. This is the default.
- **Blank sheet**: every frame empty, to draw from scratch, with the in-game Firebrand shown faintly as a guide.

You can mix and match frame by frame:

- **Import in-game frame** copies the current game version into your sheet.
- **The game's original Red Arremer** (the strip under the canvas) is there for reference and inspiration. Click a frame to pick it, then double-click or press **Import picked Red Arremer** to drop it into the current slot. If its palette line differs, the colors are matched for you.
- The **Overlay** menu shows the in-game Firebrand, Arthur's pose for this slot, or the picked Red Arremer faintly under your pixels (hold `O` to see it fully).

### The screen

- **Left side:** all of Firebrand's frame slots. Each slot is named after the move of Arthur's it replaces (A0, B9, …), and the last ones are Firebrand's own **walk** and **hover** cycles and his **wall cling** (facing right means the wall is on his left; then the same while firing).
  - Orange dot = changed.
  - "line 2" = a flames slot.
  - Slots marked like "= Walk → 1" are ones the game never shows directly. Clicking one takes you to the frame that's really used.
  - Hover a slot to see which animations use it.
- **Middle:** the zoomed 48×32 canvas. Dashed lines mark the body, the outer columns are the wings, and the faint grid marks the 8×8 hardware tiles.
- **Right side:**
  - the locked palette for this frame
  - this slot as it is in game, Arthur's pose for it, and yours
  - the **animation tester**

### Test your animations

Every move was recorded from the real game at its real speed (60 fps), and the tester plays it exactly the way the Firebrand campaign shows it: idle, walking (Firebrand's own walk cycle), crouching, jumping, throwing fire (standing, crouching and in the air), hovering, clinging to a wall (resting and firing), climbing ladders and burning up. Each one comes facing left and right.

- Pick a move from the list (or use `↑`/`↓`). It plays **your** frames next to the current in-game version.
- Your edits show up immediately.
- Pause and step with `,` and `.`, at ½× or ¼× speed if you like.
- **Click the playing animation** to jump straight to the frame being shown.

Left-facing poses are their own frames (the game doesn't mirror sprites), so remember to update both directions!

### Controls

| Action | How |
|---|---|
| Paint | Left-click / drag |
| Pick a color from the sprite | Right-click |
| Choose color | Click a swatch, or press `0`–`9`, `A`–`F` |
| Pencil / Fill / Eyedropper | `B` / `G` / `I` |
| Undo / Redo | `Ctrl/Cmd+Z` / `Ctrl/Cmd+Shift+Z` |
| Previous / next slot | `←` / `→` |
| Previous / next animation | `↑` / `↓` |
| Play / pause animation | `Space` |
| See the overlay fully | Hold `O` |

Your work **autosaves in your browser**. It's still a good idea to export now and then.

## How to send me your work

1. **Claim your frames first.** Post a comment like *"Claiming the hover cycle"* so two people don't redo the same frames.
2. Draw, and check it in the animation tester!
3. Click **Export**. You'll get two files: `firebrand_bank.bin` and `firebrand_flags.bin`.
4. Upload **both files** (zip them if that's easier) in a comment, or send them to me via LINK/EMAIL/DISCORD.
5. Optional but appreciated: click **Export PNG sheet** and post the image.

I merge only the frames you actually changed, so several people can work at once. To continue later or on another computer, use **Load .bin…** and pick `firebrand_bank.bin`.

## Tips

- Watch the animation tester often. A frame that looks fine alone can pop in motion.
- Keep the wings inside the wing columns. They're what lets him spread out wider than Arthur.
- Faded slots aren't shown in play (for example Arthur's armored frames, since Firebrand never wears armor). They're low priority.

## Credits

Everyone whose frames make it into the release will be credited. Tell me the name you'd like to be credited as.

Thanks so much! 🔥
