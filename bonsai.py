
import arcade
import math
import random
from typing import List, Optional, Tuple

#  CONSTANTS

SCREEN_W = 1280
SCREEN_H = 820
TITLE    = "Digital Bonsai"

# Tree parameters
TRUNK_LENGTH    = 105
TRUNK_THICKNESS = 13
MAX_DEPTH       = 8
GROW_SPEED      = 30
MIN_BRANCH_LEN  = 8

# Resource decay per second (base — modified by season)
WATER_DECAY_BASE    = 0.006
NUTRIENT_DECAY_BASE = 0.003

# Day/night cycle length in seconds
DAY_SECS  = 100
YEAR_DAYS = 60          # one full season cycle in real-world days

# Physics constants
GRAVITROPISM_STR = 0.012   # pull branch angles toward horizontal per second
APICAL_DOM_RATIO = 1.35    # trunk/primary branches grow this much faster
PIPE_MODEL_COEFF = 0.58    # child-thickness = parent × this per level


#  UTILITY

def lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return (int(c1[0]+(c2[0]-c1[0])*t),
            int(c1[1]+(c2[1]-c1[1])*t),
            int(c1[2]+(c2[2]-c1[2])*t))

def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)

def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)

def fill_rect(cx, cy, w, h, color):
    arcade.draw_lbwh_rectangle_filled(cx - w*0.5, cy - h*0.5, w, h, color)


#  LEAF DATA

class LeafData:
    __slots__ = ('ox','oy','size','phase','base_r','base_g','base_b','autumn_phase')

    def __init__(self):
        self.ox    = random.uniform(-26, 26)
        self.oy    = random.uniform(-26, 26)
        self.size  = random.uniform(5, 13)
        self.phase = random.uniform(0, math.tau)
        self.base_r = random.randint(14, 40)
        self.base_g = random.randint(90, 168)
        self.base_b = random.randint(12, 38)
        # Each leaf turns at a slightly different rate in autumn
        self.autumn_phase = random.uniform(0, 1)


#  WOUND / CALLUS SITE

class WoundSite:
    """Represents a pruning cut that gradually heals (callus formation)."""

    def __init__(self, x: float, y: float, thickness: float):
        self.x         = x
        self.y         = y
        self.max_thick = thickness
        self.heal_t    = 0.0   # 0 = fresh, 1 = fully healed (removed)
        self.alive     = True

    def update(self, dt: float, growth_rate: float):
        # Callus grows at a rate proportional to the tree's health/vigor
        self.heal_t += dt * 0.004 * max(0.1, growth_rate)
        if self.heal_t >= 1.0:
            self.alive = False

    def draw(self):
        if not self.alive:
            return
        r      = self.max_thick * (0.5 + 0.5 * (1.0 - self.heal_t))
        fresh  = self.heal_t < 0.25
        # Wound colour: raw cream → callus green-grey over time
        wc     = lerp_color((220, 190, 140), (105, 115, 90), self.heal_t)
        ring_c = lerp_color((160, 100,  60), ( 80,  90, 70), self.heal_t)
        arcade.draw_circle_filled(self.x, self.y, r,      wc)
        arcade.draw_circle_outline(self.x, self.y, r+1.5, ring_c, 2)
        if fresh:
            # Fresh resin glint
            arcade.draw_circle_filled(self.x+r*0.3, self.y+r*0.3, r*0.25,
                                      (240, 215, 160, 180))


#  BRANCH

class Branch:
    """One segment of the recursive bonsai structure."""

    def __init__(self, sx, sy, angle, length, thickness, depth,
                 parent=None, vigor=1.0):
        self.sx           = sx
        self.sy           = sy
        self.base_angle   = float(angle)
        self.current_angle= float(angle)   # modified by gravitropism
        self.target_len   = float(length)
        self.cur_len      = 1.0
        self.thickness    = float(thickness)
        self.depth        = depth
        self.parent       = parent
        self.vigor        = clamp(vigor, 0.1, 1.5)   # sap-flow vigor

        self.children: List['Branch'] = []
        self.leaves:   List[LeafData] = []

        self.alive            = True
        self.is_terminal      = False
        self.children_spawned = False
        self.is_pruning       = False
        self.prune_t          = 1.0

        # Dormant lateral buds (for apical release)
        self.dormant_buds    = 0

        # Wind sway
        self.sway_phase = random.uniform(0, math.tau)
        self.sway_freq  = random.uniform(0.6, 1.4)
        self.sway_amp   = 0.028 * depth / (MAX_DEPTH + 1)

        # Bark texture offset (visual variation)
        self.bark_offset = random.uniform(0, 1)

    @property
    def grown(self):
        return self.cur_len >= self.target_len * 0.98

    def live_angle(self, wind, t):
        sway = (math.sin(t * self.sway_freq + self.sway_phase)
                * self.sway_amp * wind * (self.depth + 1))
        return self.current_angle + math.degrees(sway)

    def end_pos(self, wind, t):
        a = math.radians(self.live_angle(wind, t))
        return (self.sx + math.cos(a) * self.cur_len,
                self.sy + math.sin(a) * self.cur_len)

    def static_end(self):
        a = math.radians(self.current_angle)
        return (self.sx + math.cos(a) * self.cur_len,
                self.sy + math.sin(a) * self.cur_len)

    def apply_gravitropism(self, dt):
        """Slowly bend branch angle toward horizontal (negative geotropism)."""
        if self.depth == 0:
            return
        # Branches want to deviate toward 0° (horizontal); trunk stays upright
        target = 0.0 if self.current_angle < 90 else 180.0
        pull   = (target - self.current_angle) * GRAVITROPISM_STR * dt
        self.current_angle = clamp(self.current_angle + pull, -45, 225)

    def hit(self, px, py, wind, t):
        ex, ey = self.end_pos(wind, t)
        dx, dy = ex - self.sx, ey - self.sy
        lsq    = dx*dx + dy*dy
        if lsq < 0.01:
            return math.hypot(px-self.sx, py-self.sy) < 10
        s  = clamp(((px-self.sx)*dx + (py-self.sy)*dy) / lsq, 0, 1)
        cx = self.sx + s*dx
        cy = self.sy + s*dy
        return math.hypot(px-cx, py-cy) < max(self.thickness*1.8, 8)

    def all_descendants(self):
        out = []
        for c in self.children:
            out.append(c)
            out.extend(c.all_descendants())
        return out

    @property
    def alpha(self):
        return max(0, int(255 * (self.prune_t if self.is_pruning else 1.0)))

#  PRECIPITATION PARTICLES

class RainDrop:
    __slots__ = ('x','y','vx','vy','length','alive')

    def __init__(self, stormy):
        self.x      = random.uniform(-80, SCREEN_W+80)
        self.y      = random.uniform(SCREEN_H, SCREEN_H+400)
        spd         = random.uniform(580,740) if stormy else random.uniform(290,430)
        ang_deg     = (-24 if stormy else -7) + random.uniform(-5,5)
        rad         = math.radians(ang_deg+270)
        self.vx     = math.cos(rad)*spd
        self.vy     = math.sin(rad)*spd
        self.length = random.uniform(15,26) if stormy else random.uniform(7,16)
        self.alive  = True

    def update(self, dt):
        self.x += self.vx*dt
        self.y += self.vy*dt
        if self.y < -10:
            self.alive = False


class Snowflake:
    __slots__ = ('x','y','vx','vy','size','wobble','alive')

    def __init__(self):
        self.x      = random.uniform(0, SCREEN_W)
        self.y      = random.uniform(SCREEN_H, SCREEN_H+200)
        self.vx     = random.uniform(-18, 18)
        self.vy     = -random.uniform(28, 65)
        self.size   = random.uniform(2.5, 5.5)
        self.wobble = random.uniform(0, math.tau)
        self.alive  = True

    def update(self, dt, wind):
        self.wobble += dt*1.8
        self.x += (self.vx + math.sin(self.wobble)*12 + wind*22) * dt
        self.y += self.vy*dt
        if self.y < -10 or self.x < -30 or self.x > SCREEN_W+30:
            self.alive = False


class FogParticle:
    __slots__ = ('x','y','r','alpha','vx','alive')

    def __init__(self):
        self.x     = random.uniform(-120, SCREEN_W+120)
        self.y     = random.uniform(80, SCREEN_H*0.55)
        self.r     = random.uniform(55, 130)
        self.alpha = random.randint(18, 48)
        self.vx    = random.uniform(4, 18)
        self.alive = True

    def update(self, dt, wind):
        self.x += (self.vx + wind*8)*dt
        if self.x > SCREEN_W+150:
            self.alive = False


#  ENVIRONMENT

SEASONS = ['spring', 'summer', 'autumn', 'winter']

class Environment:
    """
    Full ecosystem: pressure systems, humidity, seasonal cycles,
    evapotranspiration, frost, fog, snow.
    """

    _WEATHERS = ['sunny','cloudy','rainy','stormy','foggy']
    _WEIGHTS  = [0.38,   0.28,   0.17,   0.09,   0.08]
    _DURATION = {
        'sunny': (28,60), 'cloudy': (18,42), 'rainy': (12,28),
        'stormy': (6,18), 'foggy': (15,35),
    }
    _WIND_TGT = {
        'sunny': 0.20, 'cloudy': 0.50, 'rainy': 0.88,
        'stormy': 2.20, 'foggy': 0.10,
    }
    _SEASON_WEIGHTS = {
        # (sunny, cloudy, rainy, stormy, foggy)
        'spring': [0.38, 0.28, 0.22, 0.07, 0.05],
        'summer': [0.52, 0.24, 0.12, 0.08, 0.04],
        'autumn': [0.28, 0.32, 0.20, 0.08, 0.12],
        'winter': [0.22, 0.30, 0.18, 0.10, 0.20],
    }

    def __init__(self):
        # Resources
        self.water     = 0.68
        self.nutrients = 0.72
        self.sunlight  = 0.80
        self.health    = 0.83
        self.humidity  = 0.55    # 0-1, affects evapotranspiration
        self.soil_temp = 16.0    # Celsius — frost at < 0
        self.air_temp  = 18.0

        # Time / season
        self.time      = 0.27
        self.day_num   = 1
        self._prev     = 0.27
        self.season_idx= 0        # 0=spring 1=summer 2=autumn 3=winter
        self._day_in_season = 0

        # Pressure system (high=fair, low=storms)
        self.pressure      = 1015.0   # hPa
        self.pressure_tgt  = 1015.0
        self._pres_timer   = 0.0

        # Weather
        self.weather   = 'sunny'
        self.w_timer   = 0.0
        self.w_dur     = random.uniform(*self._DURATION['sunny'])

        # Wind
        self.wind        = 0.20
        self.wind_target = 0.20
        self.wind_gust   = 0.0    # short-burst gust
        self._gust_t     = 0.0

        # Precipitation
        self.rain:  List[RainDrop]   = []
        self.snow:  List[Snowflake]  = []
        self.fog:   List[FogParticle]= []
        self._rain_acc = 0.0
        self._snow_acc = 0.0
        self._fog_acc  = 0.0

        # Clouds
        self.cloud_x = [80.0, 340.0, 610.0, 880.0, 1150.0]
        self.cloud_y = [SCREEN_H - 95 + random.uniform(-22,22) for _ in range(5)]
        self.cloud_type = [random.choice(['cumulus','stratus']) for _ in range(5)]

    #  Derived

    @property
    def season(self):
        return SEASONS[self.season_idx]

    def daylight(self):
        return max(0.0, math.sin((self.time - 0.25)*math.tau))

    def is_frost(self):
        return self.soil_temp < 1.0

    def is_drought(self):
        return self.water < 0.12 and self.humidity < 0.30

    def sky_color(self):
        t = self.time % 1.0
        if self.season == 'winter':
            keys = [
                (0.00, ( 10, 12, 42)),
                (0.22, (210,145, 90)),
                (0.50, (155,185,220)),
                (0.78, (200,120, 80)),
                (1.00, ( 10, 12, 42)),
            ]
        elif self.season == 'autumn':
            keys = [
                (0.00, ( 10, 10, 38)),
                (0.22, (230,120, 45)),
                (0.50, (140,175,240)),
                (0.78, (220,100, 50)),
                (1.00, ( 10, 10, 38)),
            ]
        else:
            keys = [
                (0.00, (  8,  8, 35)),
                (0.22, (255,128, 42)),
                (0.50, ( 90,170,255)),
                (0.78, (255, 90, 38)),
                (1.00, (  8,  8, 35)),
            ]
        for i in range(len(keys)-1):
            t0,c0 = keys[i]; t1,c1 = keys[i+1]
            if t0 <= t <= t1:
                return lerp_color(c0, c1, smoothstep((t-t0)/(t1-t0)))
        return (8,8,35)

    def ambient(self):
        base = 0.15 + self.daylight()*0.85
        if self.weather == 'stormy':
            base *= 0.68
        if self.weather == 'foggy':
            base *= 0.80
        return clamp(base, 0.1, 1.0)

    def growth_rate(self):
        """Realistic composite growth rate."""
        # Photosynthesis limited by sunlight, CO2 (constant), leaf health
        photo = clamp(self.sunlight, 0, 1) * 0.50
        # Water uptake limited by soil moisture and temperature
        water_up = self.water * 0.30 * clamp(self.soil_temp/18.0, 0.05, 1.2)
        # Nutrient uptake
        nutr  = self.nutrients * 0.20
        res   = photo + water_up + nutr

        day_fac  = 0.10 + self.daylight()*0.90    # no growth at night
        health_f = self.health ** 1.3

        # Season modifiers
        s_mod = {'spring':1.25,'summer':1.10,'autumn':0.55,'winter':0.12}[self.season]

        # Frost shuts down growth
        if self.is_frost():
            s_mod *= 0.05

        wm = {'sunny':1.30,'cloudy':0.82,'rainy':0.95,
              'stormy':0.32,'foggy':0.70}[self.weather]

        return clamp(res * day_fac * health_f * s_mod * wm, 0.0, 1.6)

    #  Player interactions 

    def water_tree(self, amt=0.28):
        self.water = min(1.0, self.water + amt)
        self.humidity = min(1.0, self.humidity + 0.08)

    def fertilize(self, amt=0.22):
        self.nutrients = min(1.0, self.nutrients + amt)

    #  Main update 

    def update(self, dt, branches):
        self._update_time(dt)
        self._update_pressure(dt)
        self._update_weather(dt, branches)
        self._update_temperatures(dt)
        self._update_resources(dt)
        self._update_health(dt)
        self._update_wind(dt)
        self._update_precipitation(dt)
        self._drift_clouds(dt)

    def _update_time(self, dt):
        self.time = (self.time + dt/DAY_SECS) % 1.0
        if self.time < self._prev:
            self.day_num += 1
            self._day_in_season += 1
            if self._day_in_season >= YEAR_DAYS // 4:
                self._day_in_season = 0
                self.season_idx = (self.season_idx + 1) % 4
        self._prev = self.time

    def _update_pressure(self, dt):
        self._pres_timer += dt
        if self._pres_timer > random.uniform(25, 55):
            self._pres_timer = 0
            self.pressure_tgt = random.uniform(990, 1030)
        self.pressure = lerp(self.pressure, self.pressure_tgt, dt*0.05)

    def _update_temperatures(self, dt):
        """Air and soil temperature follow season + time of day."""
        s_base = {'spring':14,'summer':24,'autumn':10,'winter':-2}[self.season]
        diurnal = math.sin((self.time-0.25)*math.tau)*6.0
        self.air_temp  = lerp(self.air_temp,  s_base + diurnal, dt*0.12)
        # Soil lags 2-3 h behind air
        self.soil_temp = lerp(self.soil_temp, self.air_temp - 2.0, dt*0.04)

    def _update_resources(self, dt):
        opacity = {'sunny':1.0,'cloudy':0.40,'rainy':0.30,
                   'stormy':0.10,'foggy':0.25}[self.weather]
        self.sunlight = self.daylight() * opacity

        # Evapotranspiration — higher in summer/wind/low humidity
        et = WATER_DECAY_BASE * (1 + self.wind*0.4 + (1-self.humidity)*0.3)
        s_et = {'spring':1.0,'summer':1.4,'autumn':0.7,'winter':0.3}[self.season]
        self.water = max(0.0, self.water - et*s_et*dt)

        nd = NUTRIENT_DECAY_BASE * {'spring':1.1,'summer':1.3,
                                     'autumn':0.8,'winter':0.4}[self.season]
        self.nutrients = max(0.0, self.nutrients - nd*dt)

        # Humidity drifts toward weather target
        h_tgt = {'sunny':0.35,'cloudy':0.58,'rainy':0.90,
                  'stormy':0.95,'foggy':0.88}[self.weather]
        self.humidity = lerp(self.humidity, h_tgt, dt*0.04)

        # Rain / snow replenishment
        if self.weather in ('rainy','stormy'):
            bonus = 0.040 if self.weather=='rainy' else 0.020
            self.water = min(1.0, self.water + bonus*dt)

    def _update_health(self, dt):
        avg = (self.water + clamp(self.sunlight,0,1) + self.nutrients) / 3.0

        # Frost damage
        frost_pen = max(0.0, -self.soil_temp)*0.012 if self.is_frost() else 0.0
        # Drought stress
        drought_pen = 0.008 if self.is_drought() else 0.0
        # Waterlogging
        flood_pen = max(0.0, self.water-0.92)*0.02

        target_h = avg**1.35 - frost_pen - drought_pen - flood_pen
        self.health = clamp(
            self.health + (target_h - self.health)*0.06*dt,
            0.03, 1.0
        )

    def _update_weather(self, dt, branches):
        self.w_timer += dt
        if self.w_timer >= self.w_dur:
            self._change_weather(branches)

    def _change_weather(self, branches):
        self.w_timer = 0
        # Low pressure → wet weather; high pressure → fair
        if self.pressure < 1002:
            wts = [0.08, 0.22, 0.35, 0.28, 0.07]
        elif self.pressure > 1018:
            wts = [0.60, 0.28, 0.06, 0.01, 0.05]
        else:
            wts = self._SEASON_WEIGHTS[self.season]
        self.weather = random.choices(self._WEATHERS, wts)[0]
        self.w_dur   = random.uniform(*self._DURATION[self.weather])
        self.wind_target = self._WIND_TGT[self.weather]

        # Winter → storms are ice storms; occasionally snap branches
        storm_chance = 0.28 if self.season!='winter' else 0.40
        if self.weather=='stormy' and random.random() < storm_chance:
            candidates = [b for b in branches
                          if b.depth>1 and b.alive and not b.is_pruning]
            if candidates:
                victim = random.choice(candidates)
                victim.is_pruning = True
                for d in victim.all_descendants():
                    d.is_pruning = True
                if victim.parent and victim in victim.parent.children:
                    victim.parent.children.remove(victim)
                    victim.parent.children_spawned = False

    def _update_wind(self, dt):
        # Smooth base wind
        self.wind = lerp(self.wind, self.wind_target, min(1.0, dt*1.3))
        # Random gusts
        self._gust_t -= dt
        if self._gust_t <= 0 and self.weather in ('stormy','rainy','cloudy'):
            self._gust_t = random.uniform(3, 12)
            self.wind_gust = random.uniform(0.5, 1.8)
        self.wind_gust = max(0.0, self.wind_gust - dt*0.9)
        self.wind = min(3.0, self.wind + self.wind_gust*dt)

    def _update_precipitation(self, dt):
        # Rain 
        if self.weather in ('rainy','stormy'):
            rate = 0.014 if self.weather=='stormy' else 0.032
            self._rain_acc += dt
            while self._rain_acc >= rate:
                self._rain_acc -= rate
                self.rain.append(RainDrop(self.weather=='stormy'))
        else:
            self._rain_acc = 0.0

        for d in self.rain[:]:
            d.update(dt)
            if not d.alive:
                self.rain.remove(d)
        if len(self.rain) > 800:
            self.rain = self.rain[-800:]

        #  Snow (winter + cold)
        if self.season=='winter' and self.air_temp < 2.0:
            self._snow_acc += dt
            rate = 0.06
            while self._snow_acc >= rate:
                self._snow_acc -= rate
                self.snow.append(Snowflake())
        for s in self.snow[:]:
            s.update(dt, self.wind)
            if not s.alive:
                self.snow.remove(s)
        if len(self.snow) > 350:
            self.snow = self.snow[-350:]

        # ── Fog ──
        if self.weather=='foggy':
            self._fog_acc += dt
            if self._fog_acc > 0.8:
                self._fog_acc = 0
                self.fog.append(FogParticle())
        for f in self.fog[:]:
            f.update(dt, self.wind)
            if not f.alive:
                self.fog.remove(f)
        if len(self.fog) > 60:
            self.fog = self.fog[-60:]

    def _drift_clouds(self, dt):
        spd = 8 + self.wind*22
        for i in range(len(self.cloud_x)):
            self.cloud_x[i] = (self.cloud_x[i]+spd*dt) % (SCREEN_W+350) - 120


#  TREE

class Tree:
    """
    Bonsai structure with realistic growth physiology.

    Features:
      • Apical dominance: trunk & primary branches grow faster.
      • Pipe model: branch thickness derived from number of leaves supported.
      • Gravitropism: side branches slowly droop toward horizontal.
      • Wound sites: pruning cut calluses heal over time.
      • Apical release: pruning a tip boosts lateral bud growth.
    """

    # Bonsai style presets affect initial trunk angle + spread
    STYLES = {
        'chokkan':  {'trunk_angle': 89, 'spread': 38},   # formal upright
        'moyogi':   {'trunk_angle': 83, 'spread': 44},   # informal upright
        'shakan':   {'trunk_angle': 73, 'spread': 50},   # slanting
        'han_kengai':{'trunk_angle':55, 'spread': 56},   # semi-cascade
    }

    def __init__(self, bx, by, style='moyogi'):
        self.bx     = bx
        self.by     = by
        self.style  = style
        self.branches: List[Branch]   = []
        self.wounds:   List[WoundSite] = []

        rng = random.Random(42)
        self._moss = [(bx+rng.uniform(-72,72),
                       by+rng.uniform(-3,8),
                       rng.uniform(2.0,5.0))
                      for _ in range(14)]

        st  = self.STYLES[style]
        ang = st['trunk_angle'] + random.uniform(-3, 3)
        trunk = Branch(
            sx=bx, sy=by,
            angle=ang,
            length=TRUNK_LENGTH,
            thickness=TRUNK_THICKNESS,
            depth=0,
            vigor=1.0,
        )
        self.branches.append(trunk)

    #  Branching 

    def _grow_children(self, parent: Branch, season: str):
        if parent.depth >= MAX_DEPTH:
            parent.is_terminal = True
            if not parent.leaves:
                n = {'spring':8,'summer':7,'autumn':5,'winter':2}[season]
                parent.leaves = [LeafData() for _ in range(random.randint(n-1,n+2))]
            return

        st  = self.STYLES[self.style]
        n   = random.choices([2,3], weights=[0.52,0.48])[0]
        lr  = random.uniform(0.55, 0.70)

        spread = st['spread'] + random.uniform(-6, 6)

        if n == 2:
            deltas = [ spread+random.uniform(-8,8),
                      -spread+random.uniform(-8,8)]
        else:
            deltas = [ spread, random.uniform(-10,10), -spread]
            random.shuffle(deltas)

        ex, ey = parent.static_end()
        for delta in deltas:
            length = max(MIN_BRANCH_LEN,
                         parent.target_len * lr * random.uniform(0.82, 1.18))
            # Vigor decreases with depth (sap resistance) but boosts if
            # parent had its apex pruned (apical release)
            ap_bonus  = 1.25 if parent.dormant_buds > 0 else 1.0
            vigor     = clamp(parent.vigor * 0.78 * ap_bonus, 0.05, 1.5)

            child = Branch(
                sx=ex, sy=ey,
                angle=parent.current_angle + delta,
                length=length,
                thickness=max(1.0, parent.thickness * PIPE_MODEL_COEFF),
                depth=parent.depth+1,
                parent=parent,
                vigor=vigor,
            )
            parent.children.append(child)
            self.branches.append(child)

        parent.dormant_buds = 0   # consumed

    #  Update 

    def update(self, dt: float, env: Environment):
        gr = GROW_SPEED * env.growth_rate() * dt

        for b in self.branches:
            if not b.alive:
                continue

            if b.is_pruning:
                b.prune_t -= dt * 1.8
                if b.prune_t <= 0:
                    b.alive = False
                continue

            # Apical dominance: primary branches grow faster
            apical_boost = APICAL_DOM_RATIO ** max(0, 2-b.depth)
            local_grow   = gr * apical_boost * b.vigor

            if not b.grown:
                b.cur_len = min(b.target_len, b.cur_len + local_grow)

            if b.grown and not b.children_spawned:
                self._grow_children(b, env.season)
                b.children_spawned = True

            # Gravitropism on side branches
            if b.depth > 0:
                b.apply_gravitropism(dt)

            # Trunk secondary thickening (pipe model approximation)
            if b.depth == 0:
                leaf_count = sum(len(br.leaves) for br in self.branches
                                 if br.alive and br.is_terminal)
                target_thick = TRUNK_THICKNESS + leaf_count * 0.08
                b.thickness = lerp(b.thickness, min(28.0, target_thick), dt*0.015)
            elif b.depth < 3:
                # Sub-trunk thickening proportional to children count
                b.thickness = lerp(
                    b.thickness,
                    max(b.thickness, 1 + len(b.all_descendants())*0.06),
                    dt*0.01
                )

        self.branches = [b for b in self.branches if b.alive]

        # Update wound sites
        for w in self.wounds[:]:
            w.update(dt, env.growth_rate())
            if not w.alive:
                self.wounds.remove(w)

    #  Pruning 

    def prune(self, px, py, wind, t) -> Optional[Tuple[float, float]]:
        best = None
        for b in self.branches:
            if b.depth == 0 or b.is_pruning or not b.alive:
                continue
            if b.hit(px, py, wind, t):
                if best is None or b.depth > best.depth:
                    best = b

        if best is not None:
            cut_x, cut_y = best.sx, best.sy

            # Wound site at cut location
            self.wounds.append(WoundSite(cut_x, cut_y, best.thickness))

            # Apical release: boost parent's dormant buds
            if best.parent:
                best.parent.dormant_buds += 1
                # Allow parent to respawn children later
                if best in best.parent.children:
                    best.parent.children.remove(best)
                best.parent.children_spawned = False

            best.is_pruning = True
            for d in best.all_descendants():
                d.is_pruning = True

            return px, py
        return None



#  BONSAI APP


class BonsaiApp(arcade.Window):

    def __init__(self):
        super().__init__(SCREEN_W, SCREEN_H, TITLE, antialiasing=True)
        self.set_update_rate(1/60)

        self.env  = Environment()
        style     = random.choice(['chokkan','moyogi','shakan','han_kengai'])
        # by is the trunk base (= soil surface). rim_y = by-28, so the
        # pot body sits below this. Raise the ensemble so the whole tree
        # is visible with sky above it.
        self.tree = Tree(bx=SCREEN_W//2, by=220, style=style)

        self.t      = 0.0
        self.paused = False
        self._speed = 1.0           # simulation time multiplier
        self._fx:   List[dict] = []  # prune flash effects
        self._msgs: List[dict] = []  # notification toasts

        # Ground snow accumulation (cosmetic)
        self._snow_acc_ground = 0.0

    # Tick 

    def on_update(self, dt):
        if self.paused:
            return
        eff = dt * self._speed
        self.t += eff
        self.env.update(eff, self.tree.branches)
        self.tree.update(eff, self.env)
        for f in self._fx[:]:
            f['t'] -= dt
            if f['t'] <= 0:
                self._fx.remove(f)
        for m in self._msgs[:]:
            m['t'] -= dt
            if m['t'] <= 0:
                self._msgs.remove(m)
        # Snow accumulation on ground
        if self.env.season=='winter' and self.env.air_temp < 2.0:
            self._snow_acc_ground = min(1.0, self._snow_acc_ground + dt*0.002)
        else:
            self._snow_acc_ground = max(0.0, self._snow_acc_ground - dt*0.005)

    #  Draw 

    def on_draw(self):
        self.clear()
        self._draw_sky()
        self._draw_celestial()
        self._draw_clouds()
        self._draw_fog()
        self._draw_snow_ground()
        self._draw_rain()
        self._draw_snowflakes()
        self._draw_pot()
        self._draw_branches()
        self._draw_wounds()
        self._draw_leaves()
        self._draw_prune_fx()
        self._draw_hud()

    #  Sky 

    def _draw_sky(self):
        sc = self.env.sky_color()
        if self.env.weather == 'stormy':
            sc = tuple(max(0, c-45) for c in sc)
        elif self.env.weather == 'cloudy':
            sc = tuple(min(255, c+18) for c in sc)
        elif self.env.weather == 'foggy':
            sc = lerp_color(sc, (185,185,185), 0.45)

        horizon = (58, 48, 30)
        if self.env.season == 'autumn':
            horizon = (80, 50, 25)
        elif self.env.season == 'winter':
            horizon = (120, 120, 135)

        strips = 28
        sh = SCREEN_H / strips
        for i in range(strips):
            col = lerp_color(horizon, sc, smoothstep(i/strips))
            arcade.draw_lbwh_rectangle_filled(0, i*sh, SCREEN_W, sh+1, col)

    #  Celestial 

    def _draw_celestial(self):
        t  = self.env.time
        dl = self.env.daylight()
        if 0.20 <= t <= 0.80:
            prog = (t-0.20)/0.60
            sx = 80 + prog*(SCREEN_W-160)
            sy = SCREEN_H - 60 - math.sin(prog*math.pi)*(SCREEN_H-240)
            b  = int(255*dl)
            # Halo
            arcade.draw_circle_filled(sx, sy, 62, (b, int(b*0.80), 38, 32))
            arcade.draw_circle_filled(sx, sy, 42, (min(255,b+18), int(b*0.87), 52, 105))
            arcade.draw_circle_filled(sx, sy, 28, (min(255,b+44), int(b*0.94), 68))
        else:
            mp = ((t-0.80)%1.0)/0.40 if t>=0.80 else (t+0.20)/0.40
            mp = clamp(mp, 0, 1)
            mx = 80 + mp*(SCREEN_W-160)
            my = SCREEN_H - 60 - math.sin(mp*math.pi)*(SCREEN_H-240)
            arcade.draw_circle_filled(mx, my, 24, (210,210,195))
            sc = self.env.sky_color()
            arcade.draw_circle_filled(mx+9, my, 20, (*sc, 215))
            # Stars (only at night)
            rng = random.Random(7)
            for _ in range(55):
                sx2 = rng.uniform(0, SCREEN_W)
                sy2 = rng.uniform(SCREEN_H//2, SCREEN_H)
                br  = int(clamp((0.75-self.env.time)*3*255, 0, 255) if self.env.time < 0.25
                          else clamp((self.env.time-0.75)*3*255, 0, 255))
                if br > 20:
                    arcade.draw_circle_filled(sx2, sy2, 1.2, (br,br,br))

    # Clouds 

    def _draw_clouds(self):
        if self.env.weather not in ('cloudy','rainy','stormy','foggy'):
            return
        brt = (115 if self.env.weather=='stormy'
               else 160 if self.env.weather=='rainy'
               else 195 if self.env.weather=='cloudy'
               else 175)
        alpha = 210
        for i, (cx,cy) in enumerate(zip(self.env.cloud_x, self.env.cloud_y)):
            ct = self.env.cloud_type[i]
            cc = (brt, brt, brt+8, alpha)
            if ct == 'cumulus':
                blobs = [(-40,2,28),(-18,12,36),(6,6,32),(30,10,26),(50,2,22)]
            else:  # stratus — wide flat
                blobs = [(-60,5,20),(-30,8,22),(0,10,24),(30,8,22),(60,5,20)]
            for ox,oy,r in blobs:
                arcade.draw_ellipse_filled(cx+ox, cy+oy, r*2, r*(0.7 if ct=='stratus' else 1.0), cc)

    #  Fog 

    def _draw_fog(self):
        for f in self.env.fog:
            arcade.draw_circle_filled(f.x, f.y, f.r, (215,215,215, f.alpha))

    #  Precipitation 

    def _draw_rain(self):
        if not self.env.rain:
            return
        col = (88,118,210) if self.env.weather=='stormy' else (135,162,235)
        for d in self.env.rain:
            ex = d.x + d.vx*0.04
            ey = d.y + d.vy*0.04
            arcade.draw_line(d.x, d.y, ex, ey, (*col,162), 1)

    def _draw_snowflakes(self):
        for s in self.env.snow:
            arcade.draw_circle_filled(s.x, s.y, s.size, (235,240,255,200))
            # Simple 4-arm cross
            arcade.draw_line(s.x-s.size,s.y, s.x+s.size,s.y, (215,225,245,140), 1)
            arcade.draw_line(s.x,s.y-s.size, s.x,s.y+s.size, (215,225,245,140), 1)

    def _draw_snow_ground(self):
        if self._snow_acc_ground < 0.01:
            return
        h = int(self._snow_acc_ground * 18)
        arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_W, h+6, (228,235,248))
        # Soft top edge
        arcade.draw_ellipse_filled(SCREEN_W//2, h+4, SCREEN_W+20, 14, (228,235,248))

    #  Pot 

    def _draw_pot(self):
        """
        Realistic Japanese bonsai pot (tokoname-style rectangular).
        Layers drawn back-to-front:
          shadow → feet → body (shaded sides) → rim → glaze highlight
          → soil surface → soil texture → moss → snow
        """
        bx, by = self.tree.bx, self.tree.by
        amb = self.env.ambient()

        #  Pot geometry 
        # A tokoname pot is wide/shallow with slightly outward-flaring walls.
        # We approximate the curved profile with a 6-point polygon per face.
        POT_W   = 220    # rim half-width
        POT_WB  = 195    # base half-width  (walls taper inward)
        POT_H   = 65     # total wall height
        RIM_H   = 12     # thick flat rim at top
        BASE_H  = 9      # base band
        FOOT_H  = 8      # foot ring that lifts pot off surface
        FOOT_W  = 148    # foot ring half-width

        # by IS the soil/trunk base — pot hangs below it.
        soil_y  = by                 # trunk grows from here
        rim_y   = soil_y - 3        # rim face centre (soil ellipse straddles this)
        body_y  = rim_y  - RIM_H    # top of glazed wall face (below rim)
        base_y  = body_y - POT_H    # bottom of walls / top of foot band
        foot_y  = base_y - FOOT_H   # very bottom of pot

        # Base ceramic colour — dark unglazed tokoname (reddish-brown clay)
        # Glaze adds a cooler, slightly reflective top layer
        clay_dark  = (int(88*amb),  int(44*amb),  int(22*amb))
        clay_mid   = (int(108*amb), int(58*amb),  int(30*amb))
        clay_light = (int(132*amb), int(76*amb),  int(42*amb))
        glaze_col  = (int(72*amb),  int(38*amb),  int(20*amb))   # darker glazed face
        rim_col    = (int(118*amb), int(68*amb),  int(36*amb))
        shadow_col = (0, 0, 0, 80)

        #  Drop shadow under pot 
        arcade.draw_ellipse_filled(bx, foot_y - 4,
                                   (FOOT_W+30)*2, 14, (0, 0, 0, 55))

        #  Feet (two small rectangular feet, typical of tokoname) 
        for fx_off in (-FOOT_W*0.42, FOOT_W*0.42):
            fx = bx + fx_off
            # Foot side face (darker, facing forward-down)
            arcade.draw_polygon_filled([
                (fx - 14, base_y),
                (fx + 14, base_y),
                (fx + 12, foot_y),
                (fx - 12, foot_y),
            ], clay_dark)
            # Foot top face (catches a bit more light)
            arcade.draw_lbwh_rectangle_filled(fx-13, base_y-1, 26, 3, clay_mid)

        #  Pot body — front face (slightly curved via 8-point polygon) 
        # The wall curves: top edge wider than base, with a subtle S-curve.
        # We simulate the curve by adding intermediate points offset outward.
        curve_out = 6   # maximum outward bow of the wall mid-section
        mid_y   = (body_y + base_y) * 0.5
        mid_w   = POT_WB + (POT_W - POT_WB) * 0.5 + curve_out   # widest mid-point

        front_poly = [
            (bx - POT_WB,  base_y),          # bottom-left
            (bx + POT_WB,  base_y),           # bottom-right
            (bx + mid_w,   mid_y),            # mid-right (bowed out)
            (bx + POT_W,   body_y),           # top-right
            (bx - POT_W,   body_y),           # top-left
            (bx - mid_w,   mid_y),            # mid-left (bowed out)
        ]
        arcade.draw_polygon_filled(front_poly, glaze_col)

        #  Side shading: darker vertical gradient on left & right thirds 
        # Left shadow wedge
        arcade.draw_polygon_filled([
            (bx - POT_WB,  base_y),
            (bx - POT_WB + 32, base_y),
            (bx - mid_w + 28, mid_y),
            (bx - POT_W + 24, body_y),
            (bx - POT_W,   body_y),
            (bx - mid_w,   mid_y),
        ], (*clay_dark, 120))

        # Right shadow wedge
        arcade.draw_polygon_filled([
            (bx + POT_WB,  base_y),
            (bx + POT_WB - 32, base_y),
            (bx + mid_w - 28, mid_y),
            (bx + POT_W - 24, body_y),
            (bx + POT_W,   body_y),
            (bx + mid_w,   mid_y),
        ], (*clay_dark, 110))

        #  Vertical glaze streaks (kiln firing variation) 
        rng2 = random.Random(17)
        for _ in range(5):
            sx2 = bx + rng2.uniform(-POT_WB*0.7, POT_WB*0.7)
            streak_w = rng2.uniform(3, 9)
            streak_a = rng2.randint(12, 32)
            arcade.draw_polygon_filled([
                (sx2 - streak_w*0.5, base_y + 4),
                (sx2 + streak_w*0.5, base_y + 4),
                (sx2 + streak_w*0.3, body_y - 2),
                (sx2 - streak_w*0.3, body_y - 2),
            ], (int(155*amb), int(90*amb), int(55*amb), streak_a))

        #  Age crack lines 
        for cx_off, cy_top, cx_end, cy_bot, ca in [
            (-38, body_y-4, -28, base_y+18, 55),
            ( 55, body_y-6,  48, base_y+24, 40),
            ( 10, body_y-3,  16, mid_y,     30),
        ]:
            arcade.draw_line(bx+cx_off, cy_top, bx+cx_end, cy_bot,
                             (int(55*amb), int(25*amb), int(10*amb), ca), 1)

        #  Base band (bottom edge of walls — unglazed clay colour) 
        arcade.draw_polygon_filled([
            (bx - POT_WB,  base_y),
            (bx + POT_WB,  base_y),
            (bx + POT_WB,  base_y + BASE_H),
            (bx + mid_w - 4, base_y + BASE_H + 2),
            (bx - mid_w + 4, base_y + BASE_H + 2),
            (bx - POT_WB,  base_y + BASE_H),
        ], clay_mid)

        #  Rim — wide flat lip, lighter on top catch face 
        # Rim underside (shadow)
        arcade.draw_polygon_filled([
            (bx - POT_W - 6, rim_y),
            (bx + POT_W + 6, rim_y),
            (bx + POT_W,     body_y),
            (bx - POT_W,     body_y),
        ], clay_dark)

        # Rim top face (ellipse gives the 3-D foreshortened look)
        arcade.draw_ellipse_filled(bx, rim_y, (POT_W+8)*2, 20, rim_col)
        # Rim outer edge lip
        arcade.draw_ellipse_outline(bx, rim_y, (POT_W+8)*2, 20,
                                    clay_light, 2)

        #  Glaze specular highlight — left-of-centre vertical sheen 
        hi_x = bx - POT_W*0.28
        arcade.draw_polygon_filled([
            (hi_x - 6,  body_y + 4),
            (hi_x + 6,  body_y + 4),
            (hi_x + 3,  mid_y + 8),
            (hi_x - 3,  mid_y + 8),
        ], (int(200*amb), int(140*amb), int(100*amb), int(45*amb)))

        #  Rim specular highlight (top-left arc glow) 
        arcade.draw_ellipse_filled(bx - POT_W*0.30, rim_y + 2,
                                   int(POT_W*0.55), 6,
                                   (int(195*amb), int(145*amb), int(105*amb), int(55*amb)))

        #  Drainage hole hint (subtle dark oval on base, barely visible) 
        arcade.draw_ellipse_filled(bx, base_y - 2, 18, 6, (int(40*amb), int(18*amb), int(8*amb)))

        #  SOIL SURFACE 
        s_col = {
            'spring': (95, 62, 34),
            'summer': (82, 54, 28),
            'autumn': (78, 50, 26),
            'winter': (110, 82, 62),
        }[self.env.season]
        s_col_lit = (min(255,s_col[0]+22), min(255,s_col[1]+18), min(255,s_col[2]+10))

        # Main soil ellipse — sits at soil_y (= trunk base)
        arcade.draw_ellipse_filled(bx, soil_y, (POT_W-2)*2, 20,
                                   (int(s_col[0]*amb), int(s_col[1]*amb), int(s_col[2]*amb)))
        # Inner soil (lighter, catches light in the centre)
        arcade.draw_ellipse_filled(bx, soil_y, int((POT_W-18)*2), 14,
                                   (int(s_col_lit[0]*amb), int(s_col_lit[1]*amb), int(s_col_lit[2]*amb)))

        # Soil texture: small pebble/grit dots seeded stably
        rng3 = random.Random(55)
        for _ in range(22):
            px2   = bx + rng3.uniform(-(POT_W-22), POT_W-22)
            py2   = soil_y + rng3.uniform(-4, 4)
            pr2   = rng3.uniform(1.2, 2.8)
            shade = rng3.randint(-18, 18)
            pc    = (clamp(s_col[0]+shade, 20, 200),
                     clamp(s_col[1]+shade-4, 15, 160),
                     clamp(s_col[2]+shade-8, 8, 100))
            arcade.draw_circle_filled(px2, py2, pr2,
                                      (int(pc[0]*amb), int(pc[1]*amb), int(pc[2]*amb)))

        # Akadama / pumice aggregate highlights (light-coloured pebbles)
        rng4 = random.Random(77)
        for _ in range(8):
            px3 = bx + rng4.uniform(-(POT_W-30), POT_W-30)
            py3 = soil_y + rng4.uniform(-3, 3)
            pr3 = rng4.uniform(1.8, 3.5)
            arcade.draw_circle_filled(px3, py3, pr3,
                                      (int(165*amb), int(118*amb), int(72*amb), 180))

        #  Moss patches 
        for mx, my, mr in self.tree._moss:
            if self.env.season == 'winter':
                mc = (int(48*amb), int(68*amb), int(48*amb))
            elif self.env.season == 'autumn':
                mc = (int(55*amb), int(95*amb), int(38*amb))
            else:
                mc = (int(38*amb), int(105*amb), int(38*amb))
            # Moss blob with darker centre
            arcade.draw_circle_filled(mx, my, mr,     mc)
            arcade.draw_circle_filled(mx, my, mr*0.5,
                                      (max(0,mc[0]-12), max(0,mc[1]-18), max(0,mc[2]-8)))

        #  Snow on soil 
        if self._snow_acc_ground > 0.25:
            sw = int((POT_W - 10) * 2 * min(1.0, self._snow_acc_ground))
            arcade.draw_ellipse_filled(bx, soil_y, sw, int(12*self._snow_acc_ground + 4),
                                       (228, 235, 248, int(220*self._snow_acc_ground)))

    #  Branches 

    def _draw_branches(self):
        amb = self.env.ambient()
        for b in self.tree.branches:
            if not b.alive or b.cur_len < 1:
                continue
            ex, ey = b.end_pos(self.env.wind, self.t)
            alpha  = b.alpha
            dr     = b.depth / MAX_DEPTH

            # Realistic bark colour: trunk is reddish-grey, tips are lighter
            r  = int(clamp((62+dr*30)*amb, 0, 255))
            g  = int(clamp((38+dr*18)*amb, 0, 255))
            bl = int(clamp((22+dr*8 )*amb, 0, 255))

            # Winter: slightly bleached bark
            if self.env.season == 'winter':
                r = min(255, r+15); g = min(255, g+10); bl = min(255, bl+8)

            thick = max(1, int(b.thickness))
            arcade.draw_line(b.sx, b.sy, ex, ey, (r,g,bl,alpha), thick)

            # Subtle second line for bark texture on thick branches
            if thick >= 4:
                off = thick*0.25
                arcade.draw_line(b.sx+off, b.sy, ex+off, ey,
                                 (max(0,r-18), max(0,g-12), max(0,bl-6), alpha//3), 1)

    #  Wounds 

    def _draw_wounds(self):
        for w in self.tree.wounds:
            w.draw()

    #  Leaves 

    def _draw_leaves(self):
        amb  = self.env.ambient()
        h    = self.env.health
        s    = self.env.season

        # Autumn turn ratio (0=full green, 1=full autumn)
        autumn_r = 0.0
        if s == 'autumn':
            autumn_r = 0.55 + self._day_in_season_ratio()*0.45
        elif s == 'winter':
            autumn_r = 1.0

        for b in self.tree.branches:
            if not b.is_terminal or not b.alive or b.is_pruning or not b.leaves:
                continue
            ex, ey = b.end_pos(self.env.wind, self.t)
            alpha  = b.alpha
            sz_fac = max(0.05, h * (0.4 if s=='winter' else 1.0))

            for lf in b.leaves:
                sway = (math.sin(self.t*1.10 + b.sway_phase + lf.phase)
                        * self.env.wind * 4.2)
                lx = ex + lf.ox + sway
                ly = ey + lf.oy

                # Seasonal colour blending
                if h > 0.60 and s not in ('autumn','winter'):
                    r  = int(lf.base_r * amb)
                    g  = int(lf.base_g * amb)
                    bl = int(lf.base_b * amb)
                elif s in ('autumn','winter') or h <= 0.60:
                    # Autumn blend: green → orange/red → brown
                    ar = clamp(autumn_r + lf.autumn_phase*0.15, 0, 1)
                    if ar < 0.5:
                        # Green → yellow-orange
                        t2 = ar*2
                        r  = int(clamp(lerp(lf.base_r, 220, t2)*amb, 0,255))
                        g  = int(clamp(lerp(lf.base_g, 140, t2)*amb, 0,255))
                        bl = int(clamp(lerp(lf.base_b,  20, t2)*amb, 0,255))
                    else:
                        # Orange → dark brown
                        t2 = (ar-0.5)*2
                        r  = int(clamp(lerp(220, 75, t2)*amb, 0,255))
                        g  = int(clamp(lerp(140, 38, t2)*amb, 0,255))
                        bl = int(clamp(lerp( 20, 18, t2)*amb, 0,255))
                    if h < 0.35:
                        # Low health darkens further
                        r  = int(r*0.7); g = int(g*0.65); bl = int(bl*0.6)
                else:
                    # Stressed green (h 0.35-0.6)
                    rt = (h-0.35)/0.25
                    r  = int(clamp((lf.base_r+(1-rt)*90)*amb, 0,255))
                    g  = int(clamp((lf.base_g*rt+(1-rt)*70)*amb, 0,255))
                    bl = int(lf.base_b*amb*rt)

                sz = lf.size * sz_fac
                if sz > 0.5:
                    arcade.draw_circle_filled(lx, ly, sz, (r, g, bl, alpha))

    def _day_in_season_ratio(self):
        return clamp(self.env._day_in_season / (YEAR_DAYS//4), 0, 1)

    #  FX 

    def _draw_prune_fx(self):
        for f in self._fx:
            ratio = clamp(f['t']/0.65, 0, 1)
            a     = int(255*ratio)
            r     = 22*(1-ratio)+6
            arcade.draw_circle_outline(f['x'],f['y'], r,   (255,195,70,a), 2)
            arcade.draw_circle_filled (f['x'],f['y'], 5.5, (255,155,40,a))

    #  HUD 

    def _draw_hud(self):
        self._draw_stat_panel()
        self._draw_hint_bar()
        self._draw_notifications()
        if self.paused:
            self._draw_pause_overlay()

    def _draw_stat_panel(self):
        px, py0 = 12, SCREEN_H-12
        pw, ph  = 242, 285
        fill_rect(px+pw*0.5, py0-ph*0.5, pw, ph, (0,0,0,145))

        y = py0-28
        arcade.draw_text("BONSAI STATUS", px+6, y, (255,210,70), 13, bold=True)

        y -= 26
        self._draw_bar("Health",    self.env.health,    y, (70,215,80),  px)
        y -= 22
        self._draw_bar("Water",     self.env.water,     y, (65,155,255), px)
        y -= 22
        self._draw_bar("Sunlight",  self.env.sunlight,  y, (255,210,45), px)
        y -= 22
        self._draw_bar("Nutrients", self.env.nutrients, y, (175,115,45), px)
        y -= 22
        self._draw_bar("Humidity",  self.env.humidity,  y, (120,185,215),px)
        y -= 28

        wlabels = {'sunny':'☀ Sunny','cloudy':'⛅ Cloudy','rainy':'🌧 Rainy',
                   'stormy':'⛈ Stormy','foggy':'🌫 Foggy'}
        arcade.draw_text(f"Weather:  {wlabels[self.env.weather]}",
                         px+6, y, (195,220,255), 11)
        y -= 22

        s_col = {'spring':(140,220,130),'summer':(255,220,80),
                 'autumn':(220,130,50),'winter':(180,210,240)}[self.env.season]
        arcade.draw_text(f"Season:   {self.env.season.title()}",
                         px+6, y, s_col, 11)
        y -= 22

        arcade.draw_text(f"Air Temp: {self.env.air_temp:.1f}°C  "
                         f"({'❄ Frost!' if self.env.is_frost() else 'OK'})",
                         px+6, y, (195,195,195), 11)
        y -= 22

        hr = int(self.env.time*24)%24
        mn = int((self.env.time*24%1)*60)
        ph = "Day" if 0.25<=self.env.time<=0.75 else "Night"
        arcade.draw_text(f"Time:  {hr:02d}:{mn:02d}  ({ph})",
                         px+6, y, (195,195,195), 11)
        y -= 22

        alive = sum(1 for b in self.tree.branches if b.alive and not b.is_pruning)
        wounds = len(self.tree.wounds)
        arcade.draw_text(f"Day {self.env.day_num}   Branches:{alive}  Wounds:{wounds}",
                         px+6, y, (175,175,175), 11)
        y -= 22

        arcade.draw_text(f"Style: {self.tree.style.replace('_',' ').title()}",
                         px+6, y, (175,155,210), 11)

    def _draw_bar(self, label, val, y, colour, px):
        arcade.draw_text(f"{label}:", px+6, y, (200,200,200), 11)
        bw = 88; bx = px+115
        arcade.draw_lbwh_rectangle_filled(bx, y+1, bw, 10, (32,32,32))
        fw = max(0, int(bw*clamp(val,0,1)))
        if fw:
            arcade.draw_lbwh_rectangle_filled(bx, y+1, fw, 10, colour)
        arcade.draw_text(f"{int(clamp(val,0,1)*100)}%",
                         bx+bw+4, y, (190,190,190), 10)

    def _draw_hint_bar(self):
        arcade.draw_lbwh_rectangle_filled(0, 0, SCREEN_W, 44, (0,0,0,148))
        # Row 1 — care & flow
        row1 = ("[W] Water   [F] Fertilize   [P] Pause   "
                "[Space] Speed x1   [[] Slower   []] Faster")
        arcade.draw_text(row1, SCREEN_W//2, 25, (175,175,175), 11, anchor_x='center')
        # Row 2 — overrides & misc
        row2 = ("[T] +1hr   [N] Next day   [S] Next season   "
                "[1-5] Weather   [R] Reset   [Esc] Quit   "
                f"  Speed: x{self._speed:.2g}")
        arcade.draw_text(row2, SCREEN_W//2, 7, (130,130,130), 10, anchor_x='center')

    def _draw_notifications(self):
        """Stacked toast messages that fade out."""
        by2 = SCREEN_H // 2 + 60
        for i, m in enumerate(reversed(self._msgs[-4:])):
            ratio = clamp(m['t'] / 2.2, 0, 1)
            alpha = int(255 * min(1.0, ratio * 4))   # fast fade-in, slow fade-out
            r, g, b = m['colour']
            txt = m['text']
            # Shadow
            arcade.draw_text(txt, SCREEN_W//2+1, by2 - i*28 - 1,
                             (0,0,0,alpha//2), 16, anchor_x='center', bold=True)
            arcade.draw_text(txt, SCREEN_W//2, by2 - i*28,
                             (r, g, b, alpha), 16, anchor_x='center', bold=True)

    def _draw_pause_overlay(self):
        fill_rect(SCREEN_W//2, SCREEN_H//2, 400, 90, (0,0,0,205))
        arcade.draw_text("PAUSED", SCREEN_W//2, SCREEN_H//2+8,
                         (255,215,70), 32, anchor_x='center', bold=True)
        arcade.draw_text("[P] to resume  |  [R] to reset  |  [Esc] to quit",
                         SCREEN_W//2, SCREEN_H//2-22,
                         (180,180,180), 13, anchor_x='center')

# Input handling and notifications
    def _flash(self, msg: str, colour=(255,220,80)):
        """Show a temporary notification centre-screen."""
        self._msgs.append({'text': msg, 'colour': colour, 't': 2.2})

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            result = self.tree.prune(x, y, self.env.wind, self.t)
            if result:
                self._fx.append({'x':result[0], 'y':result[1], 't':0.65})
                self._flash("Branch pruned — lateral buds released", (255,180,60))

    def on_key_press(self, symbol, modifiers):
        k = arcade.key

        # Care
        if symbol == k.W:
            self.env.water_tree()
            self._flash("Watered  +28%", (80,160,255))
        elif symbol == k.F:
            self.env.fertilize()
            self._flash("Fertilized  +22%", (140,210,80))

        # Sim flow
        elif symbol == k.P:
            self.paused = not self.paused
            self._flash("PAUSED" if self.paused else "RESUMED")
        elif symbol == k.BRACKETLEFT:
            self._speed = max(0.25, self._speed * 0.5)
            self._flash(f"Speed x{self._speed:.2g}")
        elif symbol == k.BRACKETRIGHT:
            self._speed = min(8.0, self._speed * 2.0)
            self._flash(f"Speed x{self._speed:.2g}")
        elif symbol == k.SPACE:
            self._speed = 1.0
            self._flash("Speed reset x1")

        # Time / season skip
        elif symbol == k.T:
            self.env.time = (self.env.time + 1/24) % 1.0
            self._flash("+1 hour")
        elif symbol == k.N:
            self.env.time = 0.50
            self.env.day_num += 1
            self._flash(f"Day {self.env.day_num} — noon")
        elif symbol == k.S:
            self.env.season_idx = (self.env.season_idx + 1) % 4
            self.env._day_in_season = 0
            names = ["Spring","Summer","Autumn","Winter"]
            self._flash(f"Season -> {names[self.env.season_idx]}")

        # Weather overrides
        elif symbol == k.KEY_1:
            self.env.weather = 'sunny';  self.env.w_timer = 0; self.env.wind_target = 0.20
            self._flash("Weather: Sunny")
        elif symbol == k.KEY_2:
            self.env.weather = 'cloudy'; self.env.w_timer = 0; self.env.wind_target = 0.50
            self._flash("Weather: Cloudy")
        elif symbol == k.KEY_3:
            self.env.weather = 'rainy';  self.env.w_timer = 0; self.env.wind_target = 0.88
            self._flash("Weather: Rainy")
        elif symbol == k.KEY_4:
            self.env.weather = 'stormy'; self.env.w_timer = 0; self.env.wind_target = 2.20
            self._flash("Weather: Stormy")
        elif symbol == k.KEY_5:
            self.env.weather = 'foggy';  self.env.w_timer = 0; self.env.wind_target = 0.10
            self._flash("Weather: Foggy")

        # Reset
        elif symbol == k.R:
            style = random.choice(['chokkan','moyogi','shakan','han_kengai'])
            self.tree  = Tree(bx=SCREEN_W//2, by=220, style=style)
            self.env   = Environment()
            self._fx   = []
            self._msgs = []
            self._snow_acc_ground = 0.0
            self._flash("New bonsai planted!", (160,230,160))

        elif symbol == k.ESCAPE:
            self.close()



#  ENTRY POINT


def main():
    BonsaiApp()
    arcade.run()

if __name__ == '__main__':
    main() 
