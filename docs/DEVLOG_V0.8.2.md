# Mega Ghosts'n Goblins V0.8.2 alpha: the second loop can be finished

Hi everyone!

This update comes almost entirely from your reports. The biggest fix is the one that hurt most: **you can now finish the second loop.**

## The second loop works

If you got through the game and reached Astaroth again, you may have seen this: Arthur stuck in the room, no Astaroth, and only the music playing. That was a softlock on every second loop. It took a long time to find because it never happened when I jumped straight to that room to test it. It only happened after really finishing the first loop. Fixed, and it was waiting for Firebrand's Quest Plus players too.

## Astaroth's room, as in the arcade

- Astaroth now faces you. He was drawn mirrored, so he fought with his back turned.
- His fireballs are the arcade's.
- The room opens the way it should: "RESOLVE YOUR BATTLE !", Arthur walking in, and Princess Prin Prin beside Astaroth. She then moves away and waits on the right for the whole fight.

## Other fixes

- **Stage 6's skulls:** after really clearing stage 5, stage 6 started with 3 skulls instead of 5, and some further up were missing. They're all there now.
- **Invisible eyeballs:** the plants' eyeballs are back in the second loop.
- **Blue ravens** stay blue when they follow you out of stage 2's building, instead of turning red at the moving platforms.

## For real hardware players

V0.8.2 also has a change for a report of a freeze early in stage 1, in Home mode, on a Model 1 with an EverDrive Pro: the parallax no longer reads from the video chip during play. **I couldn't reproduce that freeze, so I can't promise this fixes it.** If you play on real hardware, please tell me whether it's gone.

## Still open

- The black square at the end of stage 2's building, and the sprite glitches before the Unicorns. I haven't been able to reproduce these yet. A screenshot or a save state from that spot would help a lot.
- The armor on stage 6's first floor, shown when you've lost yours. It may have been fixed along with the skulls, but I couldn't check it. Please let me know if you see it.

## Download & play

- **Emulators:** load the .bin in any Mega Drive / Genesis emulator with battery saves (tested in Genesis Plus GX and PicoDrive).
- **Flashcarts / real hardware:** the game saves to 8 KiB of battery SRAM on a 4 MiB cartridge, so your cart needs SRAM support at that size (most EverDrives have it).
- The version is shown at the bottom of the opening menu, so you can check which one you're on. Please mention it in your reports.

Thanks for all the reports, and thanks for playing! 👻🔥
