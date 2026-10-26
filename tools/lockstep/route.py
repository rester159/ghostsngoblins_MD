"""A scripted route both walkers can follow (the same decisions from the same positions give the same input):
ROUTE="R7278,U,L7248,U,W30,..." with R<x>/L<x> walk until Arthur's x reaches x, U/D hold up/down until y is still for
24 frames (a ladder's top takes a pause), J<n> jump right n frames held (JL<n> left, JU<n> straight up), W<n> stand n frames, F<n> fire n frames, then
stand. step(x, y) -> 'R' 'L' 'U' 'D' 'J' 'RJ' 'LJ' 'F' or '' (nothing held)."""
class Route:
    def __init__(self, spec):
        self.steps = [s for s in spec.split(',') if s]; self.i = 0; self.t = None; self.ly = None; self.still = 0

    def done(self):
        return self.i >= len(self.steps)

    def step(self, x, y):
        while self.i < len(self.steps):
            s = self.steps[self.i]; k = s[0]
            if k in 'RL' and s[1:2] != 'J':
                tx = int(s[1:])
                if (k == 'R' and x < tx) or (k == 'L' and x > tx):
                    return k
            elif k in 'UD':
                self.still = self.still + 1 if y == self.ly else 0
                self.ly = y
                if self.still <= 24:
                    return k
                self.still = 0; self.ly = None
            else:
                if self.t is None:
                    self.t = int(s[2:] if s[:2] in ('JL', 'JU') else s[1:])
                if self.t > 0:
                    self.t -= 1
                    return {'J': 'RJ', 'W': '', 'F': 'F'}[k] if s[:2] not in ('JL', 'JU') else {'JL': 'LJ', 'JU': 'J'}[s[:2]]
                self.t = None
            self.i += 1
        return ''
