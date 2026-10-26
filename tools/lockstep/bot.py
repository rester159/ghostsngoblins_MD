"""Shared walk bot: right; when x stalls 20 frames, hold up 70 frames, then
jump right; pit jump at x in AJ. step(x, y) -> 'R' / 'U' / 'J' / 'RJ'."""
class Bot:
    def __init__(self, aj, cl=()):
        self.cl = list(cl); self.climb = 0; self.ly = None; self.still = 0
        self.aj = aj; self.best = -1; self.stall = 0; self.mode = None; self.t = 0; self.jt = 0
    def step(self, x, y):
        if self.climb:
            self.still = self.still + 1 if y == self.ly else 0
            self.ly = y
            if self.still > 12:
                self.climb = 0; self.still = 0; self.best = x
            else:
                return 'U'
        for c in self.cl:
            if abs(x - c) <= 2:
                self.cl.remove(c); self.climb = 1; self.ly = y; self.still = 0
                return 'U'
        if self.jt:
            self.jt -= 1; return 'RJ'
        if any(abs(x - j) <= 1 for j in self.aj):
            self.jt = 5; return 'RJ'
        if self.mode:
            self.t -= 1
            if self.t <= 0:
                if self.mode == 'U':
                    self.mode = 'J'; self.t = 30
                else:
                    self.mode = None; self.stall = 0
            if x > self.best + 2:
                self.best = x; self.mode = None; self.stall = 0
            return {'U': 'U', 'J': 'RJ' if self.t > 24 else 'R'}.get(self.mode, 'R')
        if x > self.best:
            self.best = x; self.stall = 0
        else:
            self.stall += 1
            if self.stall > 20:
                self.mode = 'U'; self.t = 70
        return 'R'
