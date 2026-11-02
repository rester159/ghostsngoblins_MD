# Firebrand's Vendetta (experiment)

A third Home campaign beside Firebrand's Quest. It starts where the Quest ends,
with Satan dead, and runs the stages backwards to the graveyard. Arthur is the
last boss.

## Story

**The pact.** For as long as the Demon Realm has stood, Arthur's lance has cut
down Red Arremers. Firebrand thought it was war. Then, in the throne room, he
found the truth carved on a sealed tablet: Satan had made a pact with the
knight. Each time Arthur marched in to "save" the princess, Satan opened the
gates and gave him a road paved with Arremers. The Red clan was the price Satan
paid to keep his throne and his head. Every brother Firebrand ever lost was
traded away.

**The regicide.** Firebrand kills Satan in his own hall. *(The opening:
stage 6's throne room, one Satan.)*

**The vendetta.** In the Demon Realm, killing the king is the one crime
nobody forgives. The zombies, the ogres, the Big Men and the flying knights
were all bound to Satan, and every one of them now wants Firebrand dead. He
has no allies left. He also has one name left: Arthur. Firebrand flies back the
way the knight came, through the caves, the burning town and the ice palace,
until he reaches the graveyard where the knight's road began.

**The graveyard.** Arthur is waiting among the tombstones, in full armour. He
knows the pact is broken and that an Arremer has come for him. This is the
hardest fight in the game.

**Ending text (draft).**
```
THE KNIGHT HAS FALLEN.
THE PACT IS ASHES.
NO KING. NO MASTER.
THE REALM BELONGS TO
THE RED ARREMER.
```

## Structure

| Order | Stage              | Notes                                            |
|-------|--------------------|--------------------------------------------------|
| 0     | the story          | three text pages (the pact, the regicide, the vendetta) |
| 1     | stage 6, top room  | the Satan fight, then the climb out of the realm |
| 2     | stage 5            |                                                  |
| 3     | stage 4            |                                                  |
| 4     | stage 3            |                                                  |
| 5     | stage 2            |                                                  |
| 6     | stage 1, graveyard | stage boss replaced by **Arthur**                |

The stages come in reverse order, **and each map is played right to left**:
Firebrand starts at a stage's right end, beside the boss arena, and the stage
ends when he reaches its left edge, where Arthur's run started.

Built (src_patch/vendetta.c, vendetta_glue.s; hooks in tools/patch_gng.py):
- **Home menu:** FIREBRAND'S VENDETTA (`home_sub` 3, no new save fields); the
  developer menu's PLAYERS has VENDETTA for practice launches of any stage.
- **Order:** a game starts on stage 6; reaching a stage's own start
  (the game's table at $1040CC) jumps to the stage before it.
- **Far-end starts:** the game's restart entry for checkpoint 0 comes from
  `vd_starts` ($103E72). Stages 5 and 6 start two floors below the Satan
  rooms. Stage 6's set-up hard-coded the camera at the tower's foot
  ($110A2C, $119724), which loaded the map there and dropped him onto a
  wrapped floor; it now starts on him.
- **Checkpoint:** passed with the camera left of the game's mark ($103E1A)
  instead of right of it ($103CB0). A death after it restarts there.
- **Facing:** left on every start.

### Camera: always show where he's going
The game's camera ($FFF420, follow routine $10414A) holds the player 128 px
from the left and 142 px above the bottom, and scrolls down at 1, 3 or 5 px
a frame, so a long drop outruns it. In Vendetta:
- he is held **176 px from the left** (80 px from the right edge), so 176 px of
  the way ahead is on screen ($10415C gap, $1042BE new x);
- he is held **166 px above the bottom**, so 166 px below his feet is on screen
  ($1041E6 gap), and the camera scrolls down at **1, 4 or 7 px a frame**
  ($1042D0 speed table);
- each start puts the camera on him at that framing ($104372).

### Bosses
**No double bosses in this mode.** Where the game has two (stage 6's two
Satans, the Big Men pairs), Vendetta has one. The bosses fought are stage 6's
one Satan (the opening), stage 3's dragon on the route, and Arthur; the other
stages start outside their boss rooms.

### Climbing and time
Backwards, Arthur's drops are climbs (stage 3's pit and shaft, the towers'
floors). In Vendetta Firebrand also clings to solid scenery's faces (stage
3's cave stone, the towers' rock), not only the engine's wall cells, and leaps
up them; the camera climbs while he clings or hovers. Stage 2's ice towers are
background, so there is nothing to cling to there, and nothing that blocks him.
Where there is no wall (stage 2's ice towers, open drops), he **flaps**: jump
pressed again in the air is a smaller jump up, three a jump, refilled by
landing or grabbing a wall. A jump rises 40 px, with one flap 71, two 100,
three 130 (measured); the ice towers' ledges are at most 112 px apart. The
camera climbs while he flaps. Each life has a minute more than the game's
stage time. The towers go down by
their ladders (stage 3's are tiles $64-$6B, the towers' $74-$7C).

### Route checks (headless, tools/headless/fb_campaign.py REVERSE=1)
| Stage | Result |
|---|---|
| 6 | route down from Satan's room into stage 5, scripted and invincible (19,624 frames; from the old start two floors down, 2,952) |
| 5 | the same into stage 4 (12,896 frames); starts by the first ladder down, left of a brick block |
| 4 | search bot, no invincibility: cleared (4,600-11,200 frames, with and without flaps) |
| 3 | search bot, no invincibility: cleared before flaps (11,108 frames, inside the 3:28 timer); flaps only add moves. Five more seeds on the flap build stalled at the same dead-end pocket above the ladder down (x 1960): a search problem, not the map |
| 2 | search bot, no invincibility: cleared (9,200 frames; with flaps 10,572, found in a seventh of the search) |
| 1 | the bot reaches the left end; Arthur's duel there (below) |

Not checked yet: stages 5 and 6 against their enemies (the scripted runs were
invincible), and the whole run on real hardware.

### Arthur (src_patch/vd_arthur.c)
When the camera reaches stage 1's left limit with Firebrand in play, Arthur
leaps in from the side Firebrand is away from, and the screen locks: the
camera only follows past 240 px in (`vd_arena`, vendetta_glue.s
vd_cam_xgap) and Firebrand is kept at x 232 or less. The stage time stands
still and the graveyard's monsters on screen are removed (state 3) for as long
as the duel lasts.

Arthur is his own small engine, not the player's: the floor at y 62 (the
graveyard's left end is flat), a walk, the player's jump (4.25 px a frame,
gravity $3A), a crouch, and thrown lances, drawn with the game's own frames
($40000 bank: armour 0-11 facing right, their mirrors 16 and 39-48 facing
left; boxers 49-58 and 63-71; skeleton 24-33) uploaded to tile $7A0, and the
lance's art ($295000) at $7B0.
- **Two suits:** 14 fireballs take the armour off (knocked back, 60 frames
  untouchable), 14 more kill him; 40 / 30 frames of blinking after a hit.
- **Armoured:** keeps ~96 px away; throws a straight lance (5 px a frame, two
  out at most) standing, crouching, or from the top of a jump when Firebrand
  is at that height; jumps or ducks fireballs coming at him (5 in 8).
- **Boxers:** faster, comes within ~56 px, throws daggers aimed at Firebrand
  (6 px a frame, three out at most), dodges 7 in 8.
- His body or a lance kills Firebrand ($5A48's hit: physics block +4/+5);
  a fireball and a lance that meet both go. Crouching, he is under a standing
  Firebrand's fireballs (they fly at head height).
- Firebrand's death restarts the stage at its checkpoint, as anywhere;
  Arthur is back in his armour when he returns.
- Death: the skeleton falls apart (150 frames), then the ending text
  (vendetta.c vd_ending), the high-score entry, and the Home menu.

Headless (`arena.state` from a checkpoint walk, a random duel bot): without
invincibility the bot lasts 5-52 s and takes his armour off in half the runs;
an invincible bot kills him in about 1.5 min.

### The opening: Satan (vendetta.c, vendetta_glue.s)
A game starts in stage 6's top room (x 7560, floor y 2638, `vd_satan_start`,
the checkpoint-0 entry while `vd_satan_done` is 0), facing right. Stage 6 has
two Satans; the farther one is freed while still asleep (it never raised the
boss count), so it is one Satan, the game's own (satan.c), at the top rank.
His removal normally counts the stage's bosses down ($10EA0C, $FFDB09) and at
0 starts the stage-end sequence and the key ($FFDB08), which would lead to
the final room; in Vendetta it only sets `vd_satan_done` ($110558,
vd_satan_gone). Then the ladders down: a death before the regicide restarts
in his room, one after it at the old start two floors below. New games
clear the flag (settings.c player_init).

The checkpoint is passed with the camera 16 px left of the mark: stage 6's
mark is its left limit, which the camera can touch by a pixel, and that sent
a death to the tower's foot, which is Vendetta's end of the stage.

Headless: Satan's kill leaves $FFDB08 at 0 and play going on; both restart
points as above; a random bot dies in about 45 s a life having hit him 2-3
times (10 hit points); the scripted descent from his room to stage 5 takes
19,624 frames (invincible).

### Story, ending, rank
- Choosing FIREBRAND'S VENDETTA shows the story in three pages (a button each,
  Start skips); practice launches skip it.
- The ending text: THE KNIGHT HAS FALLEN. / THE PACT IS ASHES. / NO KING.
  NO MASTER. / THE DEMON REALM BELONGS TO THE RED ARREMER. / THE END.
- Everyone wants him dead: Vendetta starts at the top rank ($20, as Quest
  Plus), and the per-death decrease never goes below it.

## How each piece maps onto the existing code

| Piece | Approach | Size |
|---|---|---|
| Home menu entry | new `HOME_VENDETTA` sub beside `HOME_FIREBRAND` (boot.c), `fb_on()` true for both so all Firebrand rules apply | small |
| Reverse order | at each stage end call `stage_jump(stage - 1)` instead of the game's next stage (glue.s `stage_jump` already exists) | small |
| Start | launch at stage 6 (the debug-launch path in settings.c already does this) | small |
| "Everyone wants him dead" | built: the top starting rank (as Quest Plus) | small |
| Opening text / ending text | built: the menu screens' font (common.c), vendetta.c vd_story / vd_ending | small |
| Satan opening fight | built: stage 6's top room, one Satan, no key (below) | medium |
| **Arthur boss** | built (vd_arthur.c): his own small engine on the flat floor of the graveyard's left end, not the player-2 engine (whose weapons share Firebrand's slots and never hit a player), drawn with the game's own frames of him | large |
