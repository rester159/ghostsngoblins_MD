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

**The regicide.** Firebrand kills Satan in his own hall. *(Opening: the
Satan fight.)*

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
| 0     | Satan's hall       | opening text, then the Satan fight               |
| 1     | stage 6            | Satan already dead; the climb out of the realm   |
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
Satans, the Big Men pairs), Vendetta has one. Today's starts sit outside the
boss rooms, so no boss is fought yet. When bosses come back, each stage gets
one at most.

### Climbing and time
Backwards, Arthur's drops are climbs (stage 3's pit and shaft, the towers'
floors). In Vendetta Firebrand also clings to solid scenery's faces (stage
3's cave stone, the towers' rock), not only the engine's wall cells, and leaps
up them; the camera climbs while he clings or hovers. Stage 2's ice towers are
background, so there is nothing to cling to there, and nothing that blocks him.
Each life has a minute more than the game's stage time. The towers go down by
their ladders (stage 3's are tiles $64-$6B, the towers' $74-$7C).

### Route checks (headless, tools/headless/fb_campaign.py REVERSE=1)
| Stage | Result |
|---|---|
| 6 | route down to its start and into stage 5, scripted and invincible (2,952 frames) |
| 5 | the same into stage 4 (12,896 frames); starts by the first ladder down, left of a brick block |
| 4 | search bot, no invincibility: cleared (4,600-6,200 frames) |
| 3 | search bot, no invincibility: cleared (11,108 frames, inside the 3:28 timer) |
| 2 | search bot, no invincibility: cleared (9,200 frames) |
| 1 | the bot reaches the left end; nothing happens there yet (Arthur goes there) |

Not checked yet: stages 5 and 6 against their enemies (the scripted runs were
invincible), and the whole run on real hardware.

## How each piece maps onto the existing code

| Piece | Approach | Size |
|---|---|---|
| Home menu entry | new `HOME_VENDETTA` sub beside `HOME_FIREBRAND` (boot.c), `fb_on()` true for both so all Firebrand rules apply | small |
| Reverse order | at each stage end call `stage_jump(stage - 1)` instead of the game's next stage (glue.s `stage_jump` already exists) | small |
| Start | launch at stage 6 (the debug-launch path in settings.c already does this) | small |
| "Everyone wants him dead" | top starting rank from the start (as Quest Plus), more aggressive spawns. These are tuning knobs. | small to medium |
| Opening text / ending text | reuse ending.c's text screen (`fb_texts`) | small |
| Satan opening fight | stage 6's own Satan room, or a cut-down boss room | medium, needs research |
| **Arthur boss** | an AI Arthur on the player-2 engine (p2.c already runs a second player on Arthur's routines with a context swap). Feed it AI "pad" input in place of pad 2, draw Arthur's own frames (ARTHUR_A/B), and make the fireball and the lance hit across the two players | **large: the core of the project** |

### Arthur boss: open questions
- p2.c leaves the weapon table alone and the two players never hurt each other.
  Arthur's lances need to hit Firebrand, and Firebrand's fireballs need to hit
  Arthur, which needs new collision between player 2's body and the shot slots.
- Arthur's armour: lose it on the first hit, then the boxers, then he dies, as
  in the game. Maybe several suits for the "really tough" feel.
- AI: keep spacing, jump the fireball, throw at Firebrand's height, crouch-throw
  when he's low, change weapons (lance, dagger, torch) between phases.
- Arena: stage 1's boss area (Unicorn) with the Unicorn not spawned.
