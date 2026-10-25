# Ghosts'n Goblins MD: fixed, faster, and with two new heroes

Hi everyone!

This is **Ghosts'n Goblins MD**, my reworked version of the Ghosts'n Goblins Mega Drive / Genesis port. It runs on real hardware and accurate emulators, it's a lot faster, and it adds co-op with **Maximo** and a whole campaign as **Firebrand**, the Red Arremer. I've also got a favour to ask: see *I need artists!* below.

## How it started: fixing it

This project began as a repair job. The port is a great piece of work, but it only really behaved in older, more forgiving emulators like Fusion and Gens. On real hardware and in accuracy-focused emulators it could lock up or corrupt the screen. So the first step was a compatibility patch, with every fix checked against a disassembly of the ROM:

- **VDP port reads:** 16 instructions read the video chip's data port while writing to it. That's undefined on real hardware, and they now write only.
- **Soft reset:** the boot code now resets the VDP's command state first, so a reset in the middle of a command can't corrupt video setup.
- **Sound start-up:** the code now waits for the Z80 sound CPU's bus before writing to its RAM.
- **Attract mode:** the logo no longer draws with garbage tiles after the demo player dies.
- **A crash:** dying while blinking after a hit (time running out, falling into a pit) could halt the game. That's fixed.
- **Header:** the ROM header now has the right SRAM fields, title, size and checksum.

## Then I made it faster

With the game stable, the next problem was speed. In 1-player mode the game logic now runs at about 1.0 updates per frame in all six stages (deaths and map screens not counted). Co-op went from roughly 0.54-0.81 to 0.86-0.98, depending on the stage.

The port has no source code, so all of this was done in the 68000 machine code:

- the sound driver's request scan skips empty blocks instead of testing 512 bits one at a time
- long chains of compares in the object passes became lookup tables
- the stage 1 tombstone collision check got tightened up
- the sprite buffer is cleared in one fast block
- a **render skip** for busy moments: the game logic still runs every frame, and only the sprite drawing is skipped. Sprites are always redrawn at least every fourth frame.

I checked every optimization against the previous build. Whole frames from all six stages, with random input on both controllers, give identical RAM and video writes.

Co-op in stages 2 and 5 can still slow down when the screen is busy. I'm still working on it.

## And then I added features

**Menus and options**
- A new boot menu: **HOME** or **ARCADE**.
- **Arcade** mode plays like the cabinet: insert coins, with real **DIP switches** for coinage (including free play), lives, bonus life, difficulty, demo sound and continues.
- **Home** mode has options for lives (1-9), continues (0-9 or infinite), bonus life, difficulty, a sound test, and the **English or Japanese (Makaimura) title**.
- **Pause** with Start during play.
- **Saved high scores:** separate top-10 tables for Arcade and Home, with initials entry. They're saved to battery SRAM along with all your settings.
- The original game had no bonus life. Now it does.
- A hidden **developer menu** with stage select, infinite lives and more. You'll have to find the code. 😉

**2-player co-op with Maximo**
- Player 2 plays **Maximo** on the second controller, at the same time as Arthur.
- He uses Arthur's own movement, weapons, armor and hits, so he plays just like Arthur.
- Each player has their own lives. A fallen player respawns next to their partner, and credits let you rejoin.
- Jump on your partner's head to bounce off it.
- You share one team score.

**Firebrand's Quest**
- A single-player campaign as **Firebrand**, the Red Arremer.
- **Hover:** hold jump at the top of a jump to stay in the air for up to 2 seconds.
- He shoots **fireballs**, and pickups give points instead of new weapons.
- He has no armor: **one hit and you're dead.**
- Firebrand even shows up on the stage map and in the stage-clear scene.

## I need artists! 🎨

**The Maximo and Firebrand art is temporary.**

- **Maximo** started as Arthur's frames run through a script. He has the armor, red cape and boxers, but a lot of his frames need a human touch.
- **Firebrand** is his Demon's Crest sprite, scaled down automatically to Arthur's size. The scaling made the art muddy, and his head is a quick hand-drawn patch.

I'd love help from pixel artists. I made a **browser-based editor for each character**, so you don't need to know anything about the Mega Drive. It locks you to the right frame size and the game's palette, and it plays your frames in animations recorded from the real game at real speed, so what you draw is what shows up in-game.

- **[Maximo Pixel Editor](LINK-HERE)**
- **[Firebrand Pixel Editor](LINK-HERE)**

Each editor page explains how it works and how to send me your frames. Please **claim the frames you're working on in the comments** so two people don't redo the same ones. Everyone whose art makes it in will be credited.

Even a single cleaned-up animation helps!

## Download & play

Download **GhostsNGoblins_Plus.zip** below. It has the ROM (`Ghosts'nGoblinsMD_Alpha_0.5.bin`) and a short readme with the controls.

- **Emulators:** load the .bin in any Mega Drive / Genesis emulator with battery saves (tested in Genesis Plus GX and PicoDrive).
- **Flashcarts / real hardware:** the game saves to 8 KiB of battery SRAM on a 4 MiB cartridge, so your cart needs SRAM support at that size (most EverDrives have it). It hasn't been tested on a real console yet, so reports are very welcome.
- **Controls:** B throws, C (or A in Home mode) jumps, Start pauses. In Arcade mode C inserts a coin and A jumps. Player 2 plugs into controller 2.

Bug reports, slowdown spots and feedback are very welcome in the comments. Thanks for playing! 👻⚔️
