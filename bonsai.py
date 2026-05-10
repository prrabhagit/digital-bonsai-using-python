

import arcade
import math
import random
from typing import List, Optional, Tuple

#  CONSTANTS

SCREEN_W = 1200
SCREEN_H = 800
TITLE    = "Digital Bonsai Tree"

#  Tree parameters 
TRUNK_LENGTH    = 135     
TRUNK_THICKNESS = 14      
MAX_DEPTH       = 7       
GROW_SPEED      = 40      
MIN_BRANCH_LEN  = 12      

# Resource decay per second 
WATER_DECAY    = 0.007
NUTRIENT_DECAY = 0.004

# Day/night cycle length in seconds 
DAY_SECS = 120

#  UTILITY FUNCTIONS

def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation clamped to [a, b]."""
    return a + (b - a) * max(0.0, min(1.0, t))


def lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    """Linearly interpolate between two RGB colours."""
    t = max(0.0, min(1.0, t))
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def smoothstep(t: float) -> float:
    """Smooth S-curve easing."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def fill_rect(cx: float, cy: float, w: float, h: float, color: tuple):
    """Draw a filled rectangle centred at (cx, cy)  — arcade 3.x helper."""
    arcade.draw_lbwh_rectangle_filled(cx - w * 0.5, cy - h * 0.5, w, h, color)

#  LEAF DATA
#  Pre-computed per-leaf values — never regenerated each frame, so no flicker.

class LeafData:
    """Immutable data for a single leaf attached to a terminal branch."""

    __slots__ = ('ox', 'oy', 'size', 'phase', 'gr', 'gg', 'gb')

    def __init__(self):
        self.ox    = random.uniform(-22, 22)    # horizontal offset from tip
        self.oy    = random.uniform(-22, 22)    # vertical offset from tip
        self.size  = random.uniform(5, 12)      # base radius
        self.phase = random.uniform(0, math.pi * 2)   # unique wind phase
        # Healthy-green base RGB — health shifts hue at draw time
        self.gr = random.randint(15, 42)
        self.gg = random.randint(95, 165)
        self.gb = random.randint(15, 42)


#  BRANCH
#  One segment of the recursive bonsai structure.

class Branch:
    """
    Represents a single branch segment.

    A Branch knows its start position, its angle, and how long it currently is
    (which grows toward target_len over time).  Children are spawned once the
    branch is nearly fully grown.
    """

    def __init__(
        self,
        sx: float, sy: float,
        angle: float,
        length: float,
        thickness: float,
        depth: int,
        parent: Optional['Branch'] = None,
    ):
        # geometry parameters (mostly immutable after creation)
        self.sx           = sx
        self.sy           = sy
        self.base_angle   = float(angle)   # rest angle (no wind)
        self.target_len   = float(length)
        self.cur_len      = 1.0            # grows over time
        self.thickness    = float(thickness)
        self.depth        = depth
        self.parent       = parent

        # children & leaves 
        self.children: List['Branch']  = []
        self.leaves:   List[LeafData]  = []

        # state flags 
        self.alive            = True
        self.is_terminal      = False     # set when no further branching
        self.children_spawned = False
        self.is_pruning       = False
        self.prune_t          = 1.0       # fade timer 1 → 0

        # wind sway parameters (unique per branch) 
        self.sway_phase = random.uniform(0, math.pi * 2)
        self.sway_freq  = random.uniform(0.7, 1.5)
        # Deeper branches sway more
        self.sway_amp   = 0.030 * depth / (MAX_DEPTH + 1)

    # geometry helpers 

    @property
    def grown(self) -> bool:
        return self.cur_len >= self.target_len * 0.98

    def live_angle(self, wind: float, t: float) -> float:
        """Current display angle including wind sway."""
        sway = (math.sin(t * self.sway_freq + self.sway_phase)
                * self.sway_amp * wind * self.depth)
        return self.base_angle + math.degrees(sway)

    def end_pos(self, wind: float, t: float) -> Tuple[float, float]:
        """Tip position of this branch under current wind."""
        a = math.radians(self.live_angle(wind, t))
        return (self.sx + math.cos(a) * self.cur_len,
                self.sy + math.sin(a) * self.cur_len)

    def static_end(self) -> Tuple[float, float]:
        """Tip position with no wind (used for child placement)."""
        a = math.radians(self.base_angle)
        return (self.sx + math.cos(a) * self.cur_len,
                self.sy + math.sin(a) * self.cur_len)

    # hit-testing 

    def hit(self, px: float, py: float, wind: float, t: float) -> bool:
        """Return True if (px, py) is close enough to the branch segment."""
        ex, ey = self.end_pos(wind, t)
        dx, dy = ex - self.sx, ey - self.sy
        lsq    = dx * dx + dy * dy
        if lsq < 0.01:
            return math.hypot(px - self.sx, py - self.sy) < 10
        s  = clamp(((px - self.sx) * dx + (py - self.sy) * dy) / lsq, 0, 1)
        cx = self.sx + s * dx
        cy = self.sy + s * dy
        return math.hypot(px - cx, py - cy) < max(self.thickness * 1.6, 7)

    # traversal 

    def all_descendants(self) -> List['Branch']:
        out: List['Branch'] = []
        for c in self.children:
            out.append(c)
            out.extend(c.all_descendants())
        return out

    #visual alpha (fade during pruning) 

    @property
    def alpha(self) -> int:
        return max(0, int(255 * (self.prune_t if self.is_pruning else 1.0)))


#  RAIN DROP

class RainDrop:
    """One precipitation particle.  Spawned by Environment and drawn by the App."""

    __slots__ = ('x', 'y', 'vx', 'vy', 'length', 'alive')

    def __init__(self, stormy: bool):
        self.x      = random.uniform(-60, SCREEN_W + 60)
        self.y      = random.uniform(SCREEN_H, SCREEN_H + 350)
        spd         = random.uniform(560, 720) if stormy else random.uniform(300, 420)
        ang_deg     = (-22 if stormy else -7) + random.uniform(-4, 4)
        rad         = math.radians(ang_deg + 270)
        self.vx     = math.cos(rad) * spd
        self.vy     = math.sin(rad) * spd
        self.length = random.uniform(14, 24) if stormy else random.uniform(7, 15)
        self.alive  = True

    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y < -10:
            self.alive = False


#  ENVIRONMENT
#  Manages weather, day/night cycle, and all living resources.

class Environment:
    """
    The ecosystem that surrounds the bonsai.

    Resources (water, nutrients, sunlight, health) all live here and are
    continuously updated.  The tree reads growth_rate() to know how fast
    it should grow each frame.
    """

    _WEATHERS = ['sunny', 'cloudy', 'rainy', 'stormy']
    _WEIGHTS  = [0.40,    0.30,    0.20,    0.10]
    _DURATION = {
        'sunny':  (30, 60),
        'cloudy': (20, 40),
        'rainy':  (15, 30),
        'stormy': ( 8, 20),
    }
    _WIND_TGT = {
        'sunny': 0.22,
        'cloudy': 0.55,
        'rainy':  0.85,
        'stormy': 2.10,
    }

    def __init__(self):
        # resources 
        self.water     = 0.70
        self.nutrients = 0.75
        self.sunlight  = 0.80
        self.health    = 0.85

        # time of day 
        self.time     = 0.27        # 0 = midnight, 0.5 = noon, 1 = midnight
        self.day_num  = 1
        self._prev    = 0.27        # previous frame time (day-change detection)

        # weather 
        self.weather  = 'sunny'
        self.w_timer  = 0.0
        self.w_dur    = random.uniform(*self._DURATION['sunny'])

        # wind 
        self.wind        = 0.22
        self.wind_target = 0.22

        # precipitation particles 
        self.rain:      List[RainDrop] = []
        self._rain_acc  = 0.0

        # cloud positions (drift rightward each frame) 
        self.cloud_x = [80.0, 320.0, 590.0, 855.0, 1110.0]
        self.cloud_y = [SCREEN_H - 88 + random.uniform(-18, 18) for _ in range(5)]

    # derived quantities 

    def daylight(self) -> float:
        """0 = full night, 1 = full day — sinusoidal arc."""
        return max(0.0, math.sin((self.time - 0.25) * math.pi * 2))

    def sky_color(self) -> Tuple[int, int, int]:
        """Smoothly interpolated RGB sky colour based on time of day."""
        t = self.time % 1.0
        # Key (time, colour) pairs around the 24-hour circle
        keys: List[Tuple[float, Tuple[int, int, int]]] = [
            (0.00, (  8,   8,  35)),   # midnight — deep navy
            (0.22, (255, 128,  42)),   # pre-dawn — amber
            (0.50, ( 90, 170, 255)),   # noon     — sky blue
            (0.78, (255,  90,  38)),   # dusk     — orange-red
            (1.00, (  8,   8,  35)),   # midnight — deep navy
        ]
        for i in range(len(keys) - 1):
            t0, c0 = keys[i]
            t1, c1 = keys[i + 1]
            if t0 <= t <= t1:
                return lerp_color(c0, c1, smoothstep((t - t0) / (t1 - t0)))
        return (8, 8, 35)

    def ambient(self) -> float:
        """Screen brightness multiplier in [0.15 … 1.0]."""
        return 0.15 + self.daylight() * 0.85

    def growth_rate(self) -> float:
        """
        Composite growth speed multiplier in [0 … ~1.5].
        Affected by all resources, time of day, and weather.
        """
        res = (self.water     * 0.35
             + clamp(self.sunlight, 0, 1) * 0.40
             + self.nutrients * 0.25)
        day = 0.20 + self.daylight() * 0.80
        wm  = {
            'sunny':  1.30,
            'cloudy': 0.85,
            'rainy':  1.00,
            'stormy': 0.38,
        }[self.weather]
        return clamp(res * day * wm * self.health, 0.0, 1.5)

    # player interactions 

    def water_tree(self, amt: float = 0.25):
        self.water = min(1.0, self.water + amt)

    def fertilize(self, amt: float = 0.20):
        self.nutrients = min(1.0, self.nutrients + amt)

    # update 

    def update(self, dt: float, branches: List[Branch]):
        self._update_time(dt)
        self._update_resources(dt)
        self._update_health(dt)
        self._update_weather(dt, branches)
        self._update_wind(dt)
        self._update_precipitation(dt)
        self._drift_clouds(dt)

    def _update_time(self, dt: float):
        self.time = (self.time + dt / DAY_SECS) % 1.0
        if self.time < self._prev:       # wrapped around midnight
            self.day_num += 1
        self._prev = self.time

    def _update_resources(self, dt: float):
        # Sunlight is determined by daylight × weather cloud cover
        opacity = {
            'sunny': 1.00, 'cloudy': 0.42, 'rainy': 0.32, 'stormy': 0.12,
        }[self.weather]
        self.sunlight = self.daylight() * opacity

        # Natural decay
        self.water     = max(0.0, self.water     - WATER_DECAY    * dt)
        self.nutrients = max(0.0, self.nutrients - NUTRIENT_DECAY * dt)

        # Rain replenishes water
        if self.weather in ('rainy', 'stormy'):
            bonus = 0.038 if self.weather == 'rainy' else 0.022
            self.water = min(1.0, self.water + bonus * dt)

    def _update_health(self, dt: float):
        avg      = (self.water + clamp(self.sunlight, 0, 1) + self.nutrients) / 3
        target_h = avg ** 1.4    # non-linear — neglect punishes hard
        self.health = clamp(
            self.health + (target_h - self.health) * 0.07 * dt,
            0.05, 1.0,
        )

    def _update_weather(self, dt: float, branches: List[Branch]):
        self.w_timer += dt
        if self.w_timer >= self.w_dur:
            self._change_weather(branches)

    def _update_wind(self, dt: float):
        self.wind = lerp(self.wind, self.wind_target, min(1.0, dt * 1.4))

    def _update_precipitation(self, dt: float):
        if self.weather in ('rainy', 'stormy'):
            rate = 0.017 if self.weather == 'stormy' else 0.036
            self._rain_acc += dt
            while self._rain_acc >= rate:
                self._rain_acc -= rate
                self.rain.append(RainDrop(self.weather == 'stormy'))
        else:
            self._rain_acc = 0.0

        for d in self.rain[:]:
            d.update(dt)
            if not d.alive:
                self.rain.remove(d)
        if len(self.rain) > 700:
            self.rain = self.rain[-700:]

    def _drift_clouds(self, dt: float):
        spd = 10 + self.wind * 20
        for i in range(len(self.cloud_x)):
            self.cloud_x[i] = (self.cloud_x[i] + spd * dt) % (SCREEN_W + 300) - 100

    def _change_weather(self, branches: List[Branch]):
        self.w_timer = 0
        self.weather = random.choices(self._WEATHERS, self._WEIGHTS)[0]
        self.w_dur   = random.uniform(*self._DURATION[self.weather])
        self.wind_target = self._WIND_TGT[self.weather]

        # Storms can snap a random branch
        if self.weather == 'stormy' and random.random() < 0.30:
            candidates = [
                b for b in branches
                if b.depth > 2 and b.alive and not b.is_pruning
            ]
            if candidates:
                victim = random.choice(candidates)
                victim.is_pruning = True
                for d in victim.all_descendants():
                    d.is_pruning = True
                if victim.parent and victim in victim.parent.children:
                    victim.parent.children.remove(victim)
                    victim.parent.children_spawned = False   # allow regrowth


#  TREE
#  Manages the full bonsai structure: growth, branching, and pruning.

class Tree:
    """
    The bonsai tree itself.

    Owns all Branch objects and drives their incremental growth.
    Procedural branching is triggered automatically when a branch reaches
    ~98% of its target length.
    """

    def __init__(self, bx: float, by: float):
        self.bx = bx
        self.by = by
        self.branches: List[Branch] = []

        # Pre-generate stable moss patches (seeded so they never move)
        rng = random.Random(99)
        self._moss: List[Tuple[float, float, float]] = [
            (bx + rng.uniform(-64, 64),
             by + rng.uniform(-4, 10),
             rng.uniform(2.0, 4.5))
            for _ in range(12)
        ]

        # Plant the initial trunk
        trunk = Branch(
            sx=bx, sy=by,
            angle=89.0 + random.uniform(-4, 4),
            length=TRUNK_LENGTH,
            thickness=TRUNK_THICKNESS,
            depth=0,
        )
        self.branches.append(trunk)

    #procedural branching 

    def _grow_children(self, parent: Branch):
        """
        Procedurally spawn 2–3 child branches from a mature parent.
        All angles, lengths, and thicknesses are randomised within
        aesthetically controlled bounds.
        """
        if parent.depth >= MAX_DEPTH:
            parent.is_terminal = True
            if not parent.leaves:
                parent.leaves = [LeafData() for _ in range(random.randint(5, 9))]
            return

        n  = random.choices([2, 3], weights=[0.55, 0.45])[0]
        lr = random.uniform(0.58, 0.72)    # length ratio child/parent

        if n == 2:
            spread = random.uniform(22, 50)
            deltas = [
                 spread + random.uniform(-8, 8),
                -spread + random.uniform(-8, 8),
            ]
        else:
            a      = random.uniform(28, 46)
            deltas = [a, random.uniform(-9, 9), -a]
            random.shuffle(deltas)

        ex, ey = parent.static_end()
        for delta in deltas:
            length = max(
                MIN_BRANCH_LEN,
                parent.target_len * lr * random.uniform(0.85, 1.15)
            )
            child = Branch(
                sx=ex, sy=ey,
                angle=parent.base_angle + delta,
                length=length,
                thickness=max(1.0, parent.thickness * 0.62),
                depth=parent.depth + 1,
                parent=parent,
            )
            parent.children.append(child)
            self.branches.append(child)

    # update 

    def update(self, dt: float, env: Environment):
        grow = GROW_SPEED * env.growth_rate() * dt

        for b in self.branches:
            if not b.alive:
                continue

            if b.is_pruning:
                b.prune_t -= dt * 1.6           # fade out over ~0.6 s
                if b.prune_t <= 0:
                    b.alive = False
                continue

            # Grow toward target length
            if not b.grown:
                b.cur_len = min(b.target_len, b.cur_len + grow)

            # Spawn children once fully grown
            if b.grown and not b.children_spawned:
                self._grow_children(b)
                b.children_spawned = True

            # Trunk slowly thickens with age (cosmetic only)
            if b.depth == 0:
                b.thickness = min(24.0, b.thickness + 0.04 * dt)

        # Remove dead (fully faded) branches
        self.branches = [b for b in self.branches if b.alive]

    # pruning 

    def prune(
        self, px: float, py: float, wind: float, t: float
    ) -> Optional[Tuple[float, float]]:
        """
        Click-prune: find the deepest branch under the cursor, trigger its
        fade animation, disconnect it from its parent, and return the hit point.
        Returns None if nothing was hit.
        """
        best: Optional[Branch] = None
        for b in self.branches:
            if b.depth == 0 or b.is_pruning or not b.alive:
                continue
            if b.hit(px, py, wind, t):
                if best is None or b.depth > best.depth:
                    best = b

        if best is not None:
            best.is_pruning = True
            for d in best.all_descendants():
                d.is_pruning = True
            if best.parent and best in best.parent.children:
                best.parent.children.remove(best)
                best.parent.children_spawned = False   # parent may regrow
            return px, py

        return None


#  BONSAI APP   ── Arcade Window + event loop

class BonsaiApp(arcade.Window):
    """
    Game controller.

    Owns the Arcade window, drives the simulation tick, dispatches all
    rendering, and handles keyboard/mouse events.
    """

    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, TITLE, antialiasing=True)
        self.set_update_rate(1.0 / 60.0)

        self.env  = Environment()
        self.tree = Tree(bx=SCREEN_W // 2, by=160)

        self.t      = 0.0          # total elapsed time for animation
        self.paused = False
        # Prune visual feedback blips: list of {x, y, t}
        self._fx: List[dict] = []

    #  simulation tick 

    def on_update(self, dt: float):
        if self.paused:
            return
        self.t += dt
        self.env.update(dt, self.tree.branches)
        self.tree.update(dt, self.env)
        for f in self._fx[:]:
            f['t'] -= dt
            if f['t'] <= 0:
                self._fx.remove(f)

    #  main draw dispatch 

    def on_draw(self):
        self.clear()
        self._draw_sky()
        self._draw_celestial()
        self._draw_clouds()
        self._draw_rain()          # behind the tree
        self._draw_pot()
        self._draw_branches()
        self._draw_leaves()
        self._draw_prune_fx()
        self._draw_hud()

    #  sky 

    def _draw_sky(self):
        """
        Vertical gradient sky: warm horizon tint → sky colour at zenith.
        Storm darkens, clouds lighten.
        """
        sc = self.env.sky_color()
        if   self.env.weather == 'stormy':
            sc = tuple(max(0, c - 40) for c in sc)
        elif self.env.weather == 'cloudy':
            sc = tuple(min(255, c + 22) for c in sc)

        horizon = (55, 45, 28)
        strips  = 24
        sh      = SCREEN_H / strips
        for i in range(strips):
            col = lerp_color(horizon, sc, smoothstep(i / strips))
            arcade.draw_lbwh_rectangle_filled(
                0, i * sh, SCREEN_W, sh + 1, col)

    #  sun / moon 

    def _draw_celestial(self):
        """Draw sun or moon on an arc across the sky."""
        t  = self.env.time
        dl = self.env.daylight()

        if 0.20 <= t <= 0.80:
            # Sun travels from left to right, arcing upward at noon
            prog = (t - 0.20) / 0.60
            sx = 80 + prog * (SCREEN_W - 160)
            sy = SCREEN_H - 55 - math.sin(prog * math.pi) * (SCREEN_H - 230)
            b  = int(255 * dl)
            # Concentric glow circles
            arcade.draw_circle_filled(sx, sy, 58, (b, int(b * 0.82), 40, 35))
            arcade.draw_circle_filled(sx, sy, 40, (min(255, b+20), int(b*0.88), 55, 110))
            arcade.draw_circle_filled(sx, sy, 27, (min(255, b+45), int(b*0.94), 72))
        else:
            # Moon
            mp = ((t - 0.80) % 1.0) / 0.40 if t >= 0.80 else (t + 0.20) / 0.40
            mp = clamp(mp, 0, 1)
            mx = 80 + mp * (SCREEN_W - 160)
            my = SCREEN_H - 55 - math.sin(mp * math.pi) * (SCREEN_H - 230)
            arcade.draw_circle_filled(mx, my, 22, (208, 208, 190))
            # Crescent shadow — painted in sky colour to mask part of the disc
            sc = self.env.sky_color()
            arcade.draw_circle_filled(mx + 8, my, 19, (*sc, 210))

    #  clouds 

    def _draw_clouds(self):
        if self.env.weather not in ('cloudy', 'rainy', 'stormy'):
            return
        brt = (145 if self.env.weather == 'stormy'
               else 175 if self.env.weather == 'rainy'
               else 215)
        cc = (brt, brt, brt, 200)
        # Each cloud is a cluster of overlapping circles
        blobs = [(-36, 4, 30), (-12, 12, 37), (10, 4, 33), (33, 8, 25)]
        for cx, cy in zip(self.env.cloud_x, self.env.cloud_y):
            for ox, oy, r in blobs:
                arcade.draw_circle_filled(cx + ox, cy + oy, r, cc)

    #  rain 

    def _draw_rain(self):
        if not self.env.rain:
            return
        col = (95, 125, 215) if self.env.weather == 'stormy' else (140, 165, 238)
        for d in self.env.rain:
            # Streak: extrapolate a short tail from the drop's velocity
            ex = d.x + d.vx * 0.042
            ey = d.y + d.vy * 0.042
            arcade.draw_line(d.x, d.y, ex, ey, (*col, 165), 1)

    #  pot 

    def _draw_pot(self):
        bx, by = self.tree.bx, self.tree.by

        # Soil ellipses
        arcade.draw_ellipse_filled(bx, by + 6, 168, 30, (90, 60, 32))
        arcade.draw_ellipse_filled(bx, by + 8, 145, 22, (108, 76, 40))

        # Moss patches (pre-generated, stable positions)
        for mx, my, mr in self.tree._moss:
            arcade.draw_circle_filled(mx, my, mr, (42, 108, 42))

        # Pot body — trapezoid (wider at top)
        pw, ph, py = 158, 52, by - 26
        arcade.draw_polygon_filled(
            [(bx - pw // 2 - 14, py),
             (bx + pw // 2 + 14, py),
             (bx + pw // 2,      py - ph),
             (bx - pw // 2,      py - ph)],
            (112, 60, 30),
        )
        # Rim highlight
        fill_rect(bx, py + 5, pw + 32, 13, (138, 78, 44))
        # Base band
        fill_rect(bx, py - ph - 5, pw - 10, 9, (82, 42, 20))

    #  branches 

    def _draw_branches(self):
        """Draw all live branch segments.  Colour dims at night."""
        amb = self.env.ambient()
        for b in self.tree.branches:
            if not b.alive or b.cur_len < 1:
                continue
            ex, ey = b.end_pos(self.env.wind, self.t)
            alpha  = b.alpha
            dr     = b.depth / MAX_DEPTH

            # Wood colour lightens slightly toward tips; dims at night
            r  = int(clamp((70 + dr * 28) * amb, 0, 255))
            g  = int(clamp((42 + dr * 12) * amb, 0, 255))
            bl = int(clamp((16 + dr *  4) * amb, 0, 255))

            arcade.draw_line(
                b.sx, b.sy, ex, ey,
                (r, g, bl, alpha),
                max(1, int(b.thickness)),
            )

    #  leaves 

    def _draw_leaves(self):
        """
        Draw leaf clusters at terminal branches.
        Colour shifts green → yellow/brown as health deteriorates.
        Size scales with health.  Each leaf sways with its own phase.
        """
        amb  = self.env.ambient()
        h    = self.env.health

        for b in self.tree.branches:
            if not b.is_terminal or not b.alive or b.is_pruning or not b.leaves:
                continue
            ex, ey = b.end_pos(self.env.wind, self.t)
            alpha  = b.alpha
            sz_fac = max(0.05, h)

            for lf in b.leaves:
                sway = (math.sin(self.t * 1.12 + b.sway_phase + lf.phase)
                        * self.env.wind * 3.8)
                lx = ex + lf.ox + sway
                ly = ey + lf.oy

                if h > 0.60:
                    # Healthy — full green
                    r  = int(lf.gr * amb)
                    g  = int(lf.gg * amb)
                    bl = int(lf.gb * amb)
                elif h > 0.30:
                    # Stressed — yellowing
                    rt = (h - 0.30) / 0.30
                    r  = int(clamp((lf.gr + (1 - rt) * 120) * amb, 0, 255))
                    g  = int(clamp((lf.gg * rt + (1 - rt) * 80) * amb, 0, 255))
                    bl = int(lf.gb * amb * rt)
                else:
                    # Critical — browning
                    r  = int(clamp((95 + lf.gr) * amb, 0, 255))
                    g  = int(clamp((55 + lf.gg * 0.25) * amb, 0, 255))
                    bl = int(lf.gb * amb * 0.15)

                sz = lf.size * sz_fac
                if sz > 0.5:
                    arcade.draw_circle_filled(lx, ly, sz, (r, g, bl, alpha))

    # prune visual feedback 

    def _draw_prune_fx(self):
        """Expanding ring + dot at each pruning site."""
        for f in self._fx:
            ratio = clamp(f['t'] / 0.65, 0, 1)
            a     = int(255 * ratio)
            r     = 22 * (1 - ratio) + 6
            arcade.draw_circle_outline(f['x'], f['y'], r,   (255, 195, 70, a), 2)
            arcade.draw_circle_filled (f['x'], f['y'], 5.5, (255, 155, 40, a))

    # HUD 

    def _draw_hud(self):
        self._draw_stat_panel()
        self._draw_hint_bar()
        if self.paused:
            self._draw_pause_overlay()

    def _draw_stat_panel(self):
        """Left-side transparent panel showing all live stats."""
        px, py0 = 12, SCREEN_H - 12
        pw, ph  = 228, 215
        fill_rect(px + pw * 0.5, py0 - ph * 0.5, pw, ph, (0, 0, 0, 140))

        y = py0 - 28
        arcade.draw_text("BONSAI STATUS", px + 6, y, (255, 210, 70), 13, bold=True)

        y -= 25
        self._draw_bar("Health",    self.env.health,    y, (70,  215, 80),  px)
        y -= 22
        self._draw_bar("Water",     self.env.water,     y, (65,  155, 255), px)
        y -= 22
        self._draw_bar("Sunlight",  self.env.sunlight,  y, (255, 210, 45),  px)
        y -= 22
        self._draw_bar("Nutrients", self.env.nutrients, y, (175, 115, 45),  px)
        y -= 28

        wlabels = {
            'sunny':  'Sunny',
            'cloudy': 'Cloudy',
            'rainy':  'Rainy',
            'stormy': 'Stormy',
        }
        arcade.draw_text(
            f"Weather:  {wlabels[self.env.weather]}",
            px + 6, y, (195, 220, 255), 12,
        )
        y -= 22

        hr = int(self.env.time * 24) % 24
        mn = int((self.env.time * 24 % 1) * 60)
        ph = "Day" if 0.25 <= self.env.time <= 0.75 else "Night"
        arcade.draw_text(
            f"Time:  {hr:02d}:{mn:02d}  ({ph})",
            px + 6, y, (195, 195, 195), 11,
        )
        y -= 22

        alive = sum(
            1 for b in self.tree.branches if b.alive and not b.is_pruning
        )
        arcade.draw_text(
            f"Day {self.env.day_num}   Branches: {alive}",
            px + 6, y, (175, 175, 175), 11,
        )

    def _draw_bar(
        self, label: str, val: float, y: float, colour: tuple, px: float
    ):
        """Draw a labelled horizontal resource bar."""
        arcade.draw_text(f"{label}:", px + 6, y, (200, 200, 200), 11)
        bw  = 88
        bx  = px + 110
        # Background track
        arcade.draw_lbwh_rectangle_filled(bx, y + 1, bw, 10, (32, 32, 32))
        # Filled portion
        fw = max(0, int(bw * clamp(val, 0, 1)))
        if fw:
            arcade.draw_lbwh_rectangle_filled(bx, y + 1, fw, 10, colour)
        arcade.draw_text(
            f"{int(clamp(val, 0, 1) * 100)}%",
            bx + bw + 4, y, (190, 190, 190), 10,
        )

    def _draw_hint_bar(self):
        """Bottom-of-screen control hint strip."""
        arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_W, 30, (0, 0, 0, 130))
        arcade.draw_text(
            "Click branch to prune   |   [W] Water   |   [F] Fertilize"
            "   |   [P] Pause   |   [Esc] Quit",
            SCREEN_W // 2, 7,
            (155, 155, 155), 12,
            anchor_x='center',
        )

    def _draw_pause_overlay(self):
        fill_rect(SCREEN_W // 2, SCREEN_H // 2, 340, 70, (0, 0, 0, 190))
        arcade.draw_text(
            "PAUSED",
            SCREEN_W // 2, SCREEN_H // 2 - 14,
            (255, 215, 70), 30,
            anchor_x='center',
            bold=True,
        )

    #INPUT EVENTS

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        if button == arcade.MOUSE_BUTTON_LEFT:
            result = self.tree.prune(x, y, self.env.wind, self.t)
            if result:
                self._fx.append({'x': result[0], 'y': result[1], 't': 0.65})

    def on_key_press(self, symbol: int, modifiers: int):
        if   symbol == arcade.key.W:
            self.env.water_tree()
        elif symbol == arcade.key.F:
            self.env.fertilize()
        elif symbol == arcade.key.P:
            self.paused = not self.paused
        elif symbol == arcade.key.ESCAPE:
            arcade.close_window()


#ENTRY POINT
def main():
    BonsaiApp()
    arcade.run()


if __name__ == '__main__':
    main()
