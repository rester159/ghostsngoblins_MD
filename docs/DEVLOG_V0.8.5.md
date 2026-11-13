# Mega Ghosts'n Goblins V0.8.5 alpha: Vendetta plays left to right

Hi everyone!

## Firebrand's Vendetta now plays left to right

In Vendetta, Firebrand runs the game backwards, from Satan's throne room back to the graveyard. Until now that also meant every stage scrolled right to left, which felt odd after years of side-scrollers.

Now every stage is **mirrored**. Firebrand still goes from the end of each stage back to its start, but the whole stage is flipped, so he heads **right** across the screen like in any other side-scroller. Left and right on the pad follow the screen.

Only left and right are flipped:

- **Up and down are unchanged.** Arthur's drops are still Firebrand's climbs; they're just on the other side.
- **Text and numbers are never mirrored.** The HUD, the stage map, the story pages, and the "1000" and "200" score pop-ups over a dead boss all read normally.
- The game underneath is exactly the same: the same enemies, collisions and routes. Only the picture is turned round.

## Stage 2 fixes

- **The black block at the end of the building is gone**, and so are the stray tile bands before the Unicorns. Thanks for the reports and screenshots: the game was reading those rows of the background from the wrong place in memory.
- **Walking along the street no longer blanks the screen.** Moving from one part of the street to the next used to switch the display off for a moment while the new tiles loaded. Now only the missing tiles load, while the game keeps running.

## Stage 6: the hidden armor is back

The hidden pot on the Ogre floor appears again. If you've lost your armor, it turns into a new suit, as in the arcade.

## Still open

- The freeze early in stage 1 on a Model 1 with an EverDrive Pro. If you play on real hardware, please tell me whether you still see it.

## Download & play

- **Emulators:** load the .bin in any Mega Drive / Genesis emulator with battery saves (tested in Genesis Plus GX and PicoDrive).
- **Flashcarts / real hardware:** the game saves to 8 KiB of battery SRAM on a 4 MiB cartridge, so your cart needs SRAM support at that size (most EverDrives have it).
- **To play Vendetta:** pick **HOME**, then **FIREBRAND'S VENDETTA**.
- The version is shown at the bottom of the opening menu. Please mention it in your reports.

Thanks for playing! 👻🔥
