# v0.6 alpha: closer to the arcade, frame for frame

v0.6 is out. Most of this release is about making the Mega Drive version behave like the arcade cabinet: each of those changes was checked by running the arcade and the port side by side, headless, and comparing them frame by frame.

## Bugs you reported

- **The "invisible troll" in stage 2:** I couldn't make a Big Man disappear, but I found that every Big Man (stages 2 and 5) was drawn split down the middle, with its left half on the right. That's fixed, and it may well be what you saw. If you still run into an invisible one, please tell me exactly where.
- **Big Men walking off their ledges:** they now turn at the ledge's end and fire at Arthur, as in the arcade, and their shots last as long as the arcade's.
- **"THIS ROOM IS AN ILLUSION"** was missing half its letters after the first clear. Fixed.

## Closer to the arcade

- **Astaroth:** his walk, pauses, rapid fire, high and low shots, the 10 hits that kill him and his points now match the arcade.
- **The ending:** the timing of both clears, the texts in their arcade colours, the princess in her own colours, and the embrace (which was being drawn off screen). After the second clear the full arcade opening plays.
- **The opening:** the arcade's graveyard scene with Arthur, the princess and the armour, then the picture with the arcade's own frames: the swoop, the fall, getting up and the walk now move every frame. The HUD shows on black before stage 1, and the opening shows the real top score.
- **The Satans:** their hovering poses, the burst before the score, and the star shot.
- **Stage 2's windows** open and close with the arcade's tiles, and stay open when their devil is gone.
- **Stage 5:** the skulls stand up as skeletons, the fireball-carrying devils have their wing poses and fireball, and both die in the arcade's burst. The crows' burst now faces the arcade's way.
- **Arthur:** stepping down onto a lower floor costs a frame, a jump pressed just past a ledge's edge takes off, and riding stage 2's elevator steps like the arcade's.
- **The floor and walls under Arthur** are now the arcade's own map everywhere, so the floor checks no longer disagree after a climb.
- **Smaller timing fixes:** stage 4's fire pillars, a bonus life comes on the arcade's check frame (a few frames after the points, as on the cabinet), and the long climbs no longer lose a frame.

## Faster co-op

Co-op runs noticeably faster: stage 2 went from about 70% to 82% of full speed, the other stages are at 91-97%. The game logic is unchanged; the same code just does less work.

## Firebrand's Quest

- **Wall cling**, as in Gargoyle's Quest and Demon's Crest: in the air, push into a wall to hold on to it. Jump to leap straight up and grab it again, so walls can be climbed by hops; push away to let go. Firebrand can fire from the wall, and grabbing one refills the hover. (Walls are in stages 4-6.)
- **No more flying through rock:** the insides of the rocks in stages 5 and 6 and of stage 3's tower are now solid for Firebrand. Before, he could hover in over the top and drift around inside the stone.
- **Ladders:** he climbs them hand over hand instead of flickering between his standing and landing poses.
- **Astaroth can be beaten:** in the original only the cross hurts him, and Firebrand's fireball counted as the lance, so his shots did nothing. Now the fireball hurts him, but only if it's roughly level with him: fire early in a jump. Stage 6 also lets Firebrand through to the final room without the cross.
- **A new ending and Firebrand's Quest Plus:** beating the quest shows Firebrand's own ending and unlocks FIREBRAND'S QUEST PLUS on the title menu: enemies at top difficulty the whole way, and half the hover time. The unlock is saved, and older saves still load.

## Known issues

- Co-op can still slow down a little when the screen is busy, stage 2 most.
- A few colours are the nearest the Mega Drive's palettes allow (the ending's heart is peach, not pink).
- Maximo's and Firebrand's art is temporary (his ladder frames reuse his wall pose for now).
- Firebrand's Quest has been played through by a test bot in stages 1-4 and the final room. The towers of stages 5 and 6 haven't been finished by it yet, so tell me if you get stuck there.
- In stages 1 and 4 Firebrand can still fly in front of the buildings at the end of the stage.

As always: bug reports, slowdown spots and anything that doesn't feel like the arcade, leave a comment. The more exact the spot, the faster I can find it.
