"""
Fireboy and Watergirl – The Forest Temple
==========================================
Three progressive levels of increasing difficulty.

Controls:
  Fireboy   : WASD  (A/D = move, W = jump)
  Watergirl : Arrow Keys (LEFT/RIGHT = move, UP = jump)

Objective:
  Both characters must reach their matching exit door.
  Collect gems for bonus score.
  Fireboy dies in water pools. Watergirl dies in lava pools.
  Green/mud pools slow both characters but are safe.

Keys:
  N      – Next level (after level clear)
  R      – Restart current level (after death) / Restart all (after game win)
  ESC    – Quit

Requirements: pip install pygame
"""

import pygame
import sys
import math
import random

# ── Constants ────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1024, 640
FPS           = 60
TILE          = 32

# Palette
C_BG          = (15, 12, 30)
C_STONE       = (60, 55, 80)
C_STONE_DARK  = (40, 36, 58)
C_STONE_LIT   = (90, 84, 115)
C_LAVA        = (220, 60, 10)
C_LAVA_GLOW   = (255, 120, 30)
C_WATER       = (20, 100, 220)
C_WATER_GLOW  = (80, 180, 255)
C_MUD         = (90, 130, 60)
C_FIRE_BODY   = (230, 80, 20)
C_FIRE_HEAD   = (255, 130, 40)
C_WATER_BODY  = (30, 110, 230)
C_WATER_HEAD  = (80, 170, 255)
C_GEM_FIRE    = (255, 60, 60)
C_GEM_WATER   = (60, 180, 255)
C_GEM_GREEN   = (60, 220, 100)
C_DOOR_FIRE   = (200, 50, 10)
C_DOOR_WATER  = (10, 80, 200)
C_PLATFORM    = (110, 100, 140)
C_WHITE       = (255, 255, 255)
C_BLACK       = (0,   0,   0)
C_GOLD        = (255, 210, 40)
C_GREEN       = (40,  200, 80)
C_RED         = (200, 40,  40)

# Physics
GRAVITY    = 0.55
JUMP_POWER = -13.5
MOVE_SPEED = 4.5
MUD_SLOW   = 0.4
MAX_FALL   = 18


# ── Utility ──────────────────────────────────────────────────────────────────
def lerp_color(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_rounded_rect(surf, color, rect, r=6, alpha=None):
    if alpha is not None:
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color[:3], alpha), s.get_rect(), border_radius=r)
        surf.blit(s, rect.topleft)
    else:
        pygame.draw.rect(surf, color, rect, border_radius=r)


# ── Particle ─────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, color, vx=None, vy=None, life=None, size=None):
        self.x        = x
        self.y        = y
        self.color    = color
        self.vx       = vx   if vx   is not None else random.uniform(-2, 2)
        self.vy       = vy   if vy   is not None else random.uniform(-3, -0.5)
        self.life     = life if life is not None else random.randint(20, 45)
        self.max_life = self.life
        self.size     = size if size is not None else random.randint(2, 5)

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.1
        self.life -= 1

    def draw(self, surf):
        alpha = int(255 * self.life / self.max_life)
        t     = self.life / self.max_life
        size  = max(1, int(self.size * t))
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], alpha), (size, size), size)
        surf.blit(s, (int(self.x) - size, int(self.y) - size))


# ── Gem ──────────────────────────────────────────────────────────────────────
class Gem:
    def __init__(self, tx, ty, kind="green"):
        self.rect      = pygame.Rect(tx * TILE + 8, ty * TILE + 8, 16, 16)
        self.kind      = kind
        self.collected = False
        self.anim      = random.uniform(0, math.pi * 2)
        self.color     = {"fire": C_GEM_FIRE, "water": C_GEM_WATER, "green": C_GEM_GREEN}[kind]

    def update(self):
        self.anim += 0.06

    def draw(self, surf):
        if self.collected:
            return
        bob = math.sin(self.anim) * 3
        cx  = self.rect.centerx
        cy  = self.rect.centery + bob
        glow_s = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(glow_s, (*self.color, 50), (20, 20), 18)
        surf.blit(glow_s, (cx - 20, cy - 20))
        pts = [(cx, cy - 9), (cx + 7, cy), (cx, cy + 9), (cx - 7, cy)]
        pygame.draw.polygon(surf, self.color, pts)
        bright = lerp_color(self.color, C_WHITE, 0.6)
        pygame.draw.polygon(surf, bright, [(cx, cy - 9), (cx + 7, cy), (cx, cy)])


# ── Hazard Pool ───────────────────────────────────────────────────────────────
class HazardPool:
    def __init__(self, tx, ty, tw, th, kind="lava"):
        self.rect = pygame.Rect(tx * TILE, ty * TILE, tw * TILE, th * TILE)
        self.kind = kind
        self.anim = 0.0
        if kind == "lava":
            self.color, self.glow = C_LAVA,  C_LAVA_GLOW
        elif kind == "water":
            self.color, self.glow = C_WATER, C_WATER_GLOW
        else:
            self.color, self.glow = C_MUD,   (140, 180, 90)

    def update(self):
        self.anim += 0.04

    def draw(self, surf):
        pygame.draw.rect(surf, self.color, self.rect)
        for i in range(3):
            wx = self.rect.x + i * self.rect.width // 3
            wy = self.rect.y + 4 + int(math.sin(self.anim + i * 1.2) * 3)
            ww = self.rect.width // 3
            s  = pygame.Surface((ww, 6), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (*self.glow, 120), s.get_rect())
            surf.blit(s, (wx, wy))
        pygame.draw.line(surf, self.glow,
                         (self.rect.x, self.rect.y),
                         (self.rect.right, self.rect.y), 2)


# ── Moving Platform ───────────────────────────────────────────────────────────
class MovingPlatform:
    def __init__(self, tx, ty, tw, axis="x", dist=4, speed=1.5, phase=0.0):
        self.rect     = pygame.Rect(tx * TILE, ty * TILE, tw * TILE, TILE // 2)
        self.origin_x = self.rect.x
        self.origin_y = self.rect.y
        self.axis     = axis
        self.dist     = dist * TILE
        self.t        = phase
        self.dt       = 0.018 * speed

    def update(self):
        self.t += self.dt
        if self.t > 1.0 or self.t < 0.0:
            self.dt *= -1
            self.t = max(0.0, min(1.0, self.t))
        offset = int(math.sin(self.t * math.pi) * self.dist)
        if self.axis == "x":
            self.rect.x = self.origin_x + offset
        else:
            self.rect.y = self.origin_y + offset

    def draw(self, surf):
        shadow = pygame.Surface((self.rect.width, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 60), shadow.get_rect())
        surf.blit(shadow, (self.rect.x, self.rect.bottom + 2))
        pygame.draw.rect(surf, C_PLATFORM, self.rect, border_radius=4)
        hi = pygame.Rect(self.rect.x + 4, self.rect.y + 2, self.rect.width - 8, 3)
        pygame.draw.rect(surf, C_STONE_LIT, hi, border_radius=2)
        for bx in (self.rect.x + 6, self.rect.right - 10):
            pygame.draw.circle(surf, C_STONE_DARK, (bx, self.rect.centery), 3)


# ── Character ─────────────────────────────────────────────────────────────────
class Character:
    W, H = 22, 30

    def __init__(self, x, y, kind="fire"):
        self.kind      = kind
        self.rect      = pygame.Rect(x, y, self.W, self.H)
        self.vx        = 0.0
        self.vy        = 0.0
        self.on_ground = False
        self.alive     = True
        self.anim      = 0.0
        self.facing    = 1
        self.in_mud    = False
        self.particles = []

        if kind == "fire":
            self.body_color  = C_FIRE_BODY
            self.head_color  = C_FIRE_HEAD
            self.flame_color = C_LAVA_GLOW
        else:
            self.body_color  = C_WATER_BODY
            self.head_color  = C_WATER_HEAD
            self.flame_color = C_WATER_GLOW

    def handle_input(self, keys, left_key, right_key, jump_key):
        if not self.alive:
            return
        speed = MOVE_SPEED * (MUD_SLOW if self.in_mud else 1.0)
        if keys[left_key]:
            self.vx = -speed
            self.facing = -1
        elif keys[right_key]:
            self.vx = speed
            self.facing = 1
        else:
            self.vx *= 0.75
        if keys[jump_key] and self.on_ground:
            self.vy        = JUMP_POWER * (0.7 if self.in_mud else 1.0)
            self.on_ground = False
            for _ in range(6):
                self.particles.append(
                    Particle(self.rect.centerx, self.rect.bottom,
                             self.body_color, vy=random.uniform(-1.5, -0.5))
                )

    def apply_physics(self, tiles, moving_platforms):
        self.vy = min(self.vy + GRAVITY, MAX_FALL)
        self.rect.x += int(self.vx)
        self._resolve_x(tiles, moving_platforms)
        self.rect.y += int(self.vy)
        self._resolve_y(tiles, moving_platforms)
        self.rect.x = max(0, min(WIDTH - self.W, self.rect.x))

    def _all_rects(self, tiles, moving_platforms):
        return tiles + [p.rect for p in moving_platforms]

    def _resolve_x(self, tiles, moving_platforms):
        for r in self._all_rects(tiles, moving_platforms):
            if self.rect.colliderect(r):
                if self.vx > 0:
                    self.rect.right = r.left
                elif self.vx < 0:
                    self.rect.left  = r.right
                self.vx = 0

    def _resolve_y(self, tiles, moving_platforms):
        self.on_ground = False
        for r in self._all_rects(tiles, moving_platforms):
            if self.rect.colliderect(r):
                if self.vy > 0:
                    self.rect.bottom = r.top
                    self.vy          = 0
                    self.on_ground   = True
                elif self.vy < 0:
                    self.rect.top = r.bottom
                    self.vy       = 0

    def check_hazards(self, pools):
        self.in_mud = False
        for pool in pools:
            feet = pygame.Rect(self.rect.x + 2, self.rect.bottom - 6, self.W - 4, 8)
            if feet.colliderect(pool.rect):
                if pool.kind == "mud":
                    self.in_mud = True
                elif (self.kind == "fire"  and pool.kind == "water") or \
                     (self.kind == "water" and pool.kind == "lava"):
                    self.die()

    def die(self):
        if self.alive:
            self.alive = False
            for _ in range(20):
                self.particles.append(
                    Particle(self.rect.centerx, self.rect.centery,
                             self.body_color,
                             vx=random.uniform(-4, 4),
                             vy=random.uniform(-6, -1),
                             life=random.randint(30, 60),
                             size=random.randint(4, 8))
                )

    def collect_gems(self, gems):
        count = 0
        for g in gems:
            if not g.collected and self.rect.colliderect(g.rect):
                if (self.kind == "fire"  and g.kind in ("fire", "green")) or \
                   (self.kind == "water" and g.kind in ("water", "green")):
                    g.collected = True
                    count += 1
                    for _ in range(10):
                        self.particles.append(
                            Particle(g.rect.centerx, g.rect.centery,
                                     g.color, size=4, life=25)
                        )
        return count

    def update_anim(self):
        if abs(self.vx) > 0.5:
            self.anim += 0.18
        else:
            self.anim += 0.05
        if abs(self.vx) > 1 and random.random() < 0.3:
            self.particles.append(
                Particle(self.rect.centerx - self.facing * 8,
                         self.rect.centery + 6,
                         self.body_color, size=3, life=12)
            )
        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)
        if not self.alive:
            return
        x, y = self.rect.x, self.rect.y
        cx   = self.rect.centerx
        leg_swing = math.sin(self.anim) * 5 if abs(self.vx) > 0.5 else 0
        sh = pygame.Surface((self.W + 6, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 50), sh.get_rect())
        surf.blit(sh, (x - 3, self.rect.bottom + 1))
        gl = pygame.Surface((self.W + 16, self.H + 16), pygame.SRCALPHA)
        pygame.draw.ellipse(gl, (*self.body_color, 40), (0, 0, self.W + 16, self.H + 16))
        surf.blit(gl, (x - 8, y - 8))
        lc = lerp_color(self.body_color, C_BLACK, 0.3)
        pygame.draw.rect(surf, lc, (cx - 8, y + 18 + int(leg_swing),  7, 12), border_radius=3)
        pygame.draw.rect(surf, lc, (cx + 1, y + 18 - int(leg_swing),  7, 12), border_radius=3)
        pygame.draw.rect(surf, self.body_color,
                         pygame.Rect(x + 1, y + 10, self.W - 2, 18), border_radius=5)
        arm_swing = math.sin(self.anim) * 4 if abs(self.vx) > 0.5 else 0
        pygame.draw.rect(surf, lc, (x - 3,             y + 12 + int(arm_swing), 6, 10), border_radius=3)
        pygame.draw.rect(surf, lc, (self.rect.right-3, y + 12 - int(arm_swing), 6, 10), border_radius=3)
        pygame.draw.circle(surf, self.head_color, (cx, y + 8), 11)
        eo = self.facing * 2
        for ex in (cx + eo + 3, cx + eo - 3):
            pygame.draw.circle(surf, C_WHITE, (ex, y + 6), 4)
            pygame.draw.circle(surf, C_BLACK, (ex + self.facing, y + 6), 2)
            pygame.draw.circle(surf, C_WHITE, (ex + 1, y + 5), 1)
        if self.kind == "fire":
            for _ in range(3):
                fx = cx + random.randint(-6, 6)
                fy = y  - random.randint(2, 10)
                fs = pygame.Surface((8, 12), pygame.SRCALPHA)
                pygame.draw.ellipse(fs, (*self.flame_color, 160), fs.get_rect())
                surf.blit(fs, (fx - 4, fy - 6))
        else:
            for i in range(2):
                dx = int(cx + math.cos(self.anim + i * 3) * 10)
                dy = int(y + 4 + math.sin(self.anim + i * 3) * 5)
                pygame.draw.circle(surf, (*self.flame_color, 130), (dx, dy), 3)


# ── Door ──────────────────────────────────────────────────────────────────────
class Door:
    def __init__(self, tx, ty, kind="fire"):
        self.rect      = pygame.Rect(tx * TILE, ty * TILE - 10, TILE, TILE * 2 + 10)
        self.kind      = kind
        self.anim      = random.uniform(0, math.pi * 2)
        self.open_anim = 0.0
        self.opened    = False
        self.color     = C_DOOR_FIRE if kind == "fire" else C_DOOR_WATER
        self.glow      = C_LAVA_GLOW if kind == "fire" else C_WATER_GLOW

    def update(self, character):
        self.anim += 0.04
        if character.rect.colliderect(self.rect) and character.alive:
            self.open_anim = min(1.0, self.open_anim + 0.05)
            self.opened    = self.open_anim >= 1.0
        else:
            self.open_anim = max(0.0, self.open_anim - 0.05)

    def draw(self, surf):
        r = self.rect
        gl = pygame.Surface((r.width + 20, r.height + 20), pygame.SRCALPHA)
        a  = 40 + int(20 * math.sin(self.anim))
        pygame.draw.rect(gl, (*self.glow, a), gl.get_rect(), border_radius=8)
        surf.blit(gl, (r.x - 10, r.y - 10))
        pygame.draw.rect(surf, lerp_color(self.color, C_STONE_DARK, 0.5), r, border_radius=6)
        if self.open_anim > 0:
            open_h = int(r.height * self.open_anim)
            inner  = pygame.Rect(r.x + 4, r.bottom - open_h - 4, r.width - 8, open_h)
            s = pygame.Surface((inner.width, inner.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 200))
            surf.blit(s, inner.topleft)
        pygame.draw.rect(surf, self.color,
                         pygame.Rect(r.x + 4, r.y + 4, r.width - 8, r.height - 8),
                         border_radius=4)
        sc = r.centery
        if self.kind == "fire":
            pygame.draw.polygon(surf, self.glow,
                [(r.centerx, sc-14), (r.centerx+8, sc), (r.centerx, sc-4),
                 (r.centerx-8, sc), (r.centerx, sc+12)])
        else:
            pygame.draw.circle(surf, self.glow, (r.centerx, sc + 6), 8)
            pygame.draw.polygon(surf, self.glow,
                [(r.centerx, sc-14), (r.centerx-8, sc+2), (r.centerx+8, sc+2)])
        pygame.draw.rect(surf, self.glow, r, 2, border_radius=6)


# ── Level 1: The Antechamber ──────────────────────────────────────────────────
def build_level_1():
    """
    EASY – Generous platforms, wide spacing, only two slow moving platforms,
    small hazard pools, no tight jumps. A comfortable introduction.
    """
    tile_defs = [
        (0,  0, 32, 1), (0, 0, 1, 20), (31, 0, 1, 20), (0, 19, 32, 1),
        # Ground ledges
        (1,  15,  6, 1), (13, 15,  6, 1), (25, 15,  6, 1),
        # Mid level
        (1,  10,  5, 1), (14, 10,  4, 1), (26, 10,  5, 1),
        (5,  11,  1,  4), (26, 11, 1,  4),
        # Upper level
        (1,   5,  7, 1), (13,  5,  6, 1), (24,  5,  7, 1),
        (7,   6,  1,  4), (24,  6,  1,  4),
        # Top (doors here)
        (10,  2, 12, 1),
    ]
    tiles = _build_tiles(tile_defs)

    pools = [
        HazardPool(7,  17, 4, 2, "lava"),
        HazardPool(21, 17, 4, 2, "water"),
        HazardPool(6,  11, 2, 1, "water"),
        HazardPool(22, 11, 2, 1, "lava"),
    ]

    moving_platforms = [
        MovingPlatform(9,  14, 3, axis="x", dist=3, speed=0.8, phase=0.0),
        MovingPlatform(15,  8, 3, axis="y", dist=2, speed=0.7, phase=0.5),
    ]

    gems = [
        Gem(2,  14, "fire"),  Gem(4,  14, "fire"),
        Gem(26, 14, "water"), Gem(28, 14, "water"),
        Gem(14, 14, "green"), Gem(17, 14, "green"),
        Gem(2,   9, "fire"),  Gem(27,  9, "water"),
        Gem(16,  9, "green"),
        Gem(2,   4, "fire"),  Gem(14,  4, "green"), Gem(29, 4, "water"),
        Gem(12,  1, "fire"),  Gem(16,  1, "green"), Gem(20, 1, "water"),
    ]

    doors   = [Door(11, 1, "fire"), Door(19, 1, "water")]
    fb_pos  = (2  * TILE, 17 * TILE)
    wg_pos  = (28 * TILE, 17 * TILE)
    return tiles, pools, moving_platforms, gems, doors, fb_pos, wg_pos


# ── Level 2: The Lava Labyrinth ───────────────────────────────────────────────
def build_level_2():
    """
    MEDIUM – Tighter corridors, faster platforms, alternating lava+water pits
    force coordination, each side has a different hazard type so characters
    must take opposite routes and cannot simply follow each other.
    """
    tile_defs = [
        (0,  0, 32, 1), (0, 0, 1, 20), (31, 0, 1, 20), (0, 19, 32, 1),
        # Ground
        (1,  16,  4, 1), (7,  17,  2, 1),
        (11, 15,  3, 1), (18, 15,  3, 1),
        (22, 17,  2, 1), (27, 16,  4, 1),
        # Center dividing wall (gap at rows 10-11 for crossing)
        (15,  4,  2,  6), (15, 12,  2,  7),
        # Left mid
        (1,  11,  5, 1), (7,   9,  4, 1),
        (1,   6,  6, 1), (8,   4,  4, 1),
        # Right mid
        (19, 11,  5, 1), (21,  9,  4, 1),
        (19,  6,  6, 1), (21,  4,  4, 1),
        # Top passages
        (1,   2,  6, 1), (11,  2,  4, 1),
        (19,  2,  4, 1), (27,  2,  4, 1),
    ]
    tiles = _build_tiles(tile_defs)

    pools = [
        # Ground gauntlet
        HazardPool(5,  17, 2, 2, "lava"),
        HazardPool(9,  17, 2, 2, "water"),
        HazardPool(13, 17, 2, 2, "lava"),
        HazardPool(18, 17, 2, 2, "water"),
        HazardPool(24, 17, 2, 2, "lava"),
        # Mid
        HazardPool(6,  12, 1, 1, "water"),
        HazardPool(11, 10, 2, 1, "lava"),
        HazardPool(21, 12, 2, 1, "water"),
        HazardPool(25, 10, 2, 1, "lava"),
        # Upper
        HazardPool(2,   7, 2, 1, "water"),
        HazardPool(23,  7, 2, 1, "lava"),
        HazardPool(9,   5, 2, 1, "mud"),
        HazardPool(23,  5, 2, 1, "mud"),
    ]

    moving_platforms = [
        MovingPlatform(11, 13, 3, axis="x", dist=3, speed=1.2, phase=0.0),
        MovingPlatform(18, 13, 3, axis="x", dist=3, speed=1.2, phase=0.5),
        MovingPlatform(4,   8, 2, axis="y", dist=2, speed=1.1, phase=0.3),
        MovingPlatform(27,  8, 2, axis="y", dist=2, speed=1.1, phase=0.7),
        MovingPlatform(14,  7, 2, axis="y", dist=2, speed=1.4, phase=0.0),
    ]

    gems = [
        Gem(2,  15, "fire"),  Gem(4,  15, "fire"),
        Gem(28, 15, "water"), Gem(29, 15, "water"),
        Gem(12, 14, "green"), Gem(19, 14, "green"),
        Gem(2,  10, "fire"),  Gem(8,   8, "fire"),
        Gem(25, 10, "water"), Gem(28,  8, "water"),
        Gem(14,  9, "green"),
        Gem(2,   5, "fire"),  Gem(9,   3, "fire"),
        Gem(25,  5, "water"), Gem(21,  3, "water"),
        Gem(12,  1, "green"), Gem(21,  1, "green"),
    ]

    doors  = [Door(1, 1, "fire"), Door(28, 1, "water")]
    fb_pos = (2  * TILE, 15 * TILE)
    wg_pos = (28 * TILE, 15 * TILE)
    return tiles, pools, moving_platforms, gems, doors, fb_pos, wg_pos


# ── Level 3: The Crystal Crucible ─────────────────────────────────────────────
def build_level_3():
    """
    HARD – Fast platforms, dense alternating hazard pools, narrow landings,
    characters must take completely separate routes through the level and
    only reunite at the very top. Mud pools slow you right before the final jump.
    """
    tile_defs = [
        (0,  0, 32, 1), (0, 0, 1, 20), (31, 0, 1, 20), (0, 19, 32, 1),
        # Tiny landings
        (1,  18,  2, 1), (29, 18,  2, 1),
        (14, 17,  4, 1),
        # Lower floor
        (1,  14,  3, 1), (6,  15,  2, 1),
        (10, 13,  3, 1), (14, 14,  4, 1),
        (19, 13,  3, 1), (24, 15,  2, 1), (28, 14,  3, 1),
        # Mid
        (1,  10,  3, 1), (5,  11,  2, 1),
        (9,   9,  2, 1), (13, 10,  2, 1),
        (17, 10,  2, 1), (21,  9,  2, 1),
        (25, 11,  2, 1), (28, 10,  3, 1),
        # Outer walls with gaps (force routing)
        (6,   5,  1,  5), (25,  5,  1,  5),
        # Upper
        (1,   6,  4, 1), (7,   5,  3, 1),
        (12,  6,  4, 1), (16,  6,  4, 1),
        (22,  5,  3, 1), (27,  6,  4, 1),
        # Top
        (1,   2,  5, 1), (9,   3,  4, 1),
        (14,  2,  4, 1),
        (19,  3,  4, 1), (26,  2,  5, 1),
    ]
    tiles = _build_tiles(tile_defs)

    pools = [
        # Ground gauntlet – alternating lava/water
        HazardPool(3,  18, 3, 1, "water"), HazardPool(6,  18, 2, 1, "lava"),
        HazardPool(8,  18, 3, 1, "water"), HazardPool(11, 18, 3, 1, "lava"),
        HazardPool(18, 18, 3, 1, "water"), HazardPool(21, 18, 3, 1, "lava"),
        HazardPool(24, 18, 3, 1, "water"), HazardPool(27, 18, 2, 1, "lava"),
        # Lower
        HazardPool(4,  15, 2, 1, "water"), HazardPool(22, 15, 2, 1, "lava"),
        HazardPool(11, 14, 1, 1, "lava"),  HazardPool(20, 14, 1, 1, "water"),
        # Mid
        HazardPool(3,  11, 2, 1, "water"), HazardPool(10, 10, 1, 1, "lava"),
        HazardPool(14, 11, 1, 1, "water"), HazardPool(17, 11, 1, 1, "lava"),
        HazardPool(21, 10, 1, 1, "water"), HazardPool(26, 11, 2, 1, "lava"),
        # Upper
        HazardPool(2,   7, 2, 1, "water"), HazardPool(8,   6, 2, 1, "lava"),
        HazardPool(13,  7, 1, 1, "water"), HazardPool(18,  7, 1, 1, "lava"),
        HazardPool(22,  6, 2, 1, "water"), HazardPool(28,  7, 2, 1, "lava"),
        # Mud slowdowns before the final climb
        HazardPool(9,   4, 2, 1, "mud"),   HazardPool(21,  4, 2, 1, "mud"),
        HazardPool(14,  3, 4, 1, "mud"),
    ]

    moving_platforms = [
        # Ground crossings (fast, over death pools)
        MovingPlatform(3,  17, 2, axis="x", dist=4, speed=1.8, phase=0.0),
        MovingPlatform(19, 17, 2, axis="x", dist=4, speed=1.8, phase=0.5),
        # Lower verticals
        MovingPlatform(7,  14, 2, axis="y", dist=2, speed=1.4, phase=0.2),
        MovingPlatform(23, 14, 2, axis="y", dist=2, speed=1.4, phase=0.8),
        # Mid horizontals (tight timing)
        MovingPlatform(11,  9, 2, axis="x", dist=2, speed=2.0, phase=0.0),
        MovingPlatform(19,  9, 2, axis="x", dist=2, speed=2.0, phase=0.5),
        # Upper fast verticals
        MovingPlatform(4,   5, 2, axis="y", dist=3, speed=1.6, phase=0.0),
        MovingPlatform(26,  5, 2, axis="y", dist=3, speed=1.6, phase=0.5),
        # Top bridges
        MovingPlatform(10,  2, 3, axis="x", dist=3, speed=1.5, phase=0.3),
        MovingPlatform(18,  2, 3, axis="x", dist=3, speed=1.5, phase=0.7),
    ]

    gems = [
        Gem(1,  17, "fire"),  Gem(29, 17, "water"),
        Gem(14, 16, "green"), Gem(17, 16, "green"),
        Gem(1,  13, "fire"),  Gem(11, 12, "fire"),
        Gem(29, 13, "water"), Gem(20, 12, "water"),
        Gem(15, 13, "green"),
        Gem(1,   9, "fire"),  Gem(9,   8, "fire"),
        Gem(29,  9, "water"), Gem(22,  8, "water"),
        Gem(14,  9, "green"), Gem(17,  9, "green"),
        Gem(1,   5, "fire"),  Gem(7,   4, "fire"),
        Gem(28,  5, "water"), Gem(23,  4, "water"),
        Gem(13,  5, "green"), Gem(18,  5, "green"),
        Gem(1,   1, "fire"),  Gem(9,   2, "fire"),
        Gem(30,  1, "water"), Gem(21,  2, "water"),
        Gem(14,  1, "green"), Gem(17,  1, "green"),
    ]

    doors  = [Door(14, 1, "fire"), Door(17, 1, "water")]
    fb_pos = (1  * TILE, 17 * TILE)
    wg_pos = (29 * TILE, 17 * TILE)
    return tiles, pools, moving_platforms, gems, doors, fb_pos, wg_pos


# ── Shared tile builder ───────────────────────────────────────────────────────
def _build_tiles(tile_defs):
    tiles = []
    for (tx, ty, tw, th) in tile_defs:
        for c in range(tw):
            for r in range(th):
                tiles.append(pygame.Rect((tx + c) * TILE, (ty + r) * TILE, TILE, TILE))
    return tiles


LEVEL_BUILDERS = [build_level_1, build_level_2, build_level_3]
LEVEL_NAMES    = [
    "Level 1 – The Antechamber",
    "Level 2 – The Lava Labyrinth",
    "Level 3 – The Crystal Crucible",
]
LEVEL_THEMES   = [
    (20, 18, 40),  # L1: cool purple
    (35, 12,  8),  # L2: fiery dark red
    (10, 18, 42),  # L3: deep ocean blue
]


def load_level(idx):
    tiles, pools, moving_platforms, gems, doors, fb_pos, wg_pos = LEVEL_BUILDERS[idx]()
    fireboy   = Character(fb_pos[0], fb_pos[1], "fire")
    watergirl = Character(wg_pos[0], wg_pos[1], "water")
    return tiles, pools, moving_platforms, gems, doors, fireboy, watergirl


# ── Rendering helpers ─────────────────────────────────────────────────────────
def draw_background(surf, tick, lvl):
    surf.fill(LEVEL_THEMES[lvl])
    gc = tuple(max(0, c - 10) for c in LEVEL_THEMES[lvl])
    for x in range(0, WIDTH, TILE):
        pygame.draw.line(surf, gc, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, TILE):
        pygame.draw.line(surf, gc, (0, y), (WIDTH, y))
    for tx, ty in [(4*TILE, 5*TILE), (16*TILE, 5*TILE), (28*TILE, 5*TILE),
                   (4*TILE, 11*TILE), (28*TILE, 11*TILE)]:
        flicker = 0.6 + 0.4 * math.sin(tick * 0.12 + tx)
        r = int(30 * flicker)
        gl = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(gl, (200, 120, 20, int(60 * flicker)), (r, r), r)
        surf.blit(gl, (tx - r, ty - r))
        pygame.draw.rect(surf, (90, 60, 30), (tx-3, ty, 6, 14), border_radius=2)
        pygame.draw.circle(surf, (230, 120, 20), (tx, ty-2), 5)
        pygame.draw.circle(surf, C_GOLD, (tx, ty-4), 3)


def draw_tiles(surf, tiles):
    for r in tiles:
        pygame.draw.rect(surf, C_STONE, r)
        pygame.draw.rect(surf, C_STONE_DARK, r.inflate(-4, -4))
        pygame.draw.line(surf, C_STONE_LIT, r.topleft, r.topright)
        pygame.draw.line(surf, C_STONE_LIT, r.topleft, r.bottomleft)


def draw_hud(surf, lvl, level_score, total_gems, fb_alive, wg_alive,
             total_score, font, small_font, tick):
    hud = pygame.Surface((WIDTH, 44), pygame.SRCALPHA)
    hud.fill((10, 8, 22, 215))
    surf.blit(hud, (0, 0))

    fb_col = C_FIRE_HEAD if fb_alive else C_RED
    pygame.draw.circle(surf, fb_col, (22, 22), 14)
    pygame.draw.circle(surf, C_FIRE_BODY, (22, 22), 14, 2)
    if not fb_alive:
        pygame.draw.line(surf, C_RED, (15,15),(29,29),3)
        pygame.draw.line(surf, C_RED, (29,15),(15,29),3)
    surf.blit(small_font.render("FIREBOY  WASD", True, fb_col), (42, 13))

    wg_col = C_WATER_HEAD if wg_alive else C_RED
    pygame.draw.circle(surf, wg_col, (WIDTH-22, 22), 14)
    pygame.draw.circle(surf, C_WATER_BODY, (WIDTH-22, 22), 14, 2)
    if not wg_alive:
        pygame.draw.line(surf, C_RED, (WIDTH-29,15),(WIDTH-15,29),3)
        pygame.draw.line(surf, C_RED, (WIDTH-15,15),(WIDTH-29,29),3)
    wt = small_font.render("ARROW KEYS  WATERGIRL", True, wg_col)
    surf.blit(wt, wt.get_rect(right=WIDTH-42, centery=22))

    anim = math.sin(tick * 0.08) * 2
    pts  = [(WIDTH//2-32, int(22-10+anim)), (WIDTH//2-25, int(22+anim)),
            (WIDTH//2-32, int(22+10+anim)), (WIDTH//2-39, int(22+anim))]
    pygame.draw.polygon(surf, C_GEM_GREEN, pts)

    label = f"{LEVEL_NAMES[lvl]}   {level_score}/{total_gems}  |  Total: {total_score}"
    ct = font.render(label, True, C_GOLD)
    surf.blit(ct, ct.get_rect(centerx=WIDTH//2 + 12, centery=22))


def draw_overlay(surf, font, big_font, title, lines, color):
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 175))
    surf.blit(ov, (0, 0))
    panel = pygame.Rect(WIDTH//2 - 310, HEIGHT//2 - 120, 620, 240)
    draw_rounded_rect(surf, (20, 16, 40), panel, r=16)
    pygame.draw.rect(surf, color, panel, 3, border_radius=16)
    t1 = big_font.render(title, True, color)
    surf.blit(t1, t1.get_rect(centerx=WIDTH//2, centery=HEIGHT//2 - 55))
    for i, line in enumerate(lines):
        t = font.render(line, True, C_WHITE)
        surf.blit(t, t.get_rect(centerx=WIDTH//2, centery=HEIGHT//2 + 5 + i * 30))


def draw_fade(surf, alpha, lvl, font, big_font):
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, int(alpha)))
    surf.blit(ov, (0, 0))
    if alpha > 120:
        ta = max(0, min(255, int((alpha - 120) * 2.1)))
        t1 = big_font.render(LEVEL_NAMES[lvl], True, C_GOLD)
        t2 = font.render("Get ready – both heroes must reach their door!", True, C_WHITE)
        t1.set_alpha(ta); t2.set_alpha(ta)
        surf.blit(t1, t1.get_rect(centerx=WIDTH//2, centery=HEIGHT//2 - 30))
        surf.blit(t2, t2.get_rect(centerx=WIDTH//2, centery=HEIGHT//2 + 25))


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Fireboy & Watergirl – The Forest Temple")
    clock  = pygame.time.Clock()

    try:
        font       = pygame.font.SysFont("segoeui", 18, bold=True)
        big_font   = pygame.font.SysFont("segoeui", 46, bold=True)
        small_font = pygame.font.SysFont("segoeui", 15)
    except Exception:
        font       = pygame.font.Font(None, 22)
        big_font   = pygame.font.Font(None, 54)
        small_font = pygame.font.Font(None, 18)

    current_level = 0
    total_score   = 0

    tiles, pools, moving_platforms, gems, doors, fireboy, watergirl = load_level(current_level)
    total_gems   = len(gems)
    level_score  = 0

    tick         = 0
    state        = "fade_in"
    fade_alpha   = 255.0
    bg_particles = []

    def restart_level():
        nonlocal tiles, pools, moving_platforms, gems, doors, fireboy, watergirl
        nonlocal total_gems, level_score, state, fade_alpha, tick
        tiles, pools, moving_platforms, gems, doors, fireboy, watergirl = load_level(current_level)
        total_gems  = len(gems)
        level_score = 0
        state       = "fade_in"
        fade_alpha  = 255.0
        tick        = 0

    def next_level():
        nonlocal current_level, tiles, pools, moving_platforms, gems, doors
        nonlocal fireboy, watergirl, total_gems, level_score, state, fade_alpha, tick
        current_level += 1
        tiles, pools, moving_platforms, gems, doors, fireboy, watergirl = load_level(current_level)
        total_gems  = len(gems)
        level_score = 0
        state       = "fade_in"
        fade_alpha  = 255.0
        tick        = 0

    while True:
        clock.tick(FPS)
        tick += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if state == "lose":
                    if event.key == pygame.K_r:
                        restart_level()
                elif state == "level_win":
                    if event.key == pygame.K_n:
                        next_level()
                    elif event.key == pygame.K_r:
                        current_level = 0
                        total_score   = 0
                        restart_level()
                elif state == "game_win":
                    if event.key == pygame.K_r:
                        current_level = 0
                        total_score   = 0
                        restart_level()

        keys = pygame.key.get_pressed()

        # ── Fade in ───────────────────────────────────────────────────────────
        if state == "fade_in":
            fade_alpha -= 5.0
            if fade_alpha <= 0:
                fade_alpha = 0
                state = "playing"

        # ── Playing ───────────────────────────────────────────────────────────
        if state == "playing":
            fireboy.handle_input(keys, pygame.K_a, pygame.K_d, pygame.K_w)
            watergirl.handle_input(keys, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP)
            fireboy.apply_physics(tiles, moving_platforms)
            watergirl.apply_physics(tiles, moving_platforms)
            fireboy.check_hazards(pools)
            watergirl.check_hazards(pools)
            for mp in moving_platforms:
                mp.update()
            level_score += fireboy.collect_gems(gems)
            level_score += watergirl.collect_gems(gems)
            doors[0].update(fireboy)
            doors[1].update(watergirl)
            fireboy.update_anim()
            watergirl.update_anim()
            for g in gems:  g.update()
            for p in pools: p.update()
            for ch in (fireboy, watergirl):
                if ch.rect.top > HEIGHT and ch.alive:
                    ch.die()
            if not fireboy.alive or not watergirl.alive:
                state = "lose"
            if doors[0].opened and doors[1].opened:
                total_score += level_score
                if current_level >= len(LEVEL_BUILDERS) - 1:
                    state = "game_win"
                else:
                    state = "level_win"

        # ── Ambient particles ─────────────────────────────────────────────────
        if tick % 8 == 0:
            bg_particles.append(
                Particle(random.randint(TILE, WIDTH - TILE), HEIGHT - TILE,
                         random.choice([C_LAVA_GLOW, C_WATER_GLOW]),
                         vy=random.uniform(-1.5, -0.4),
                         life=random.randint(60, 120),
                         size=random.randint(1, 3))
            )
        for p in bg_particles[:]:
            p.update()
            if p.life <= 0:
                bg_particles.remove(p)

        # ── Draw ──────────────────────────────────────────────────────────────
        draw_background(screen, tick, current_level)
        for p in bg_particles: p.draw(screen)
        draw_tiles(screen, tiles)
        for pool in pools:  pool.draw(screen)
        for mp in moving_platforms: mp.draw(screen)
        for g in gems:  g.draw(screen)
        for d in doors: d.draw(screen)
        fireboy.draw(screen)
        watergirl.draw(screen)
        draw_hud(screen, current_level, level_score, total_gems,
                 fireboy.alive, watergirl.alive, total_score, font, small_font, tick)

        # ── Overlays ──────────────────────────────────────────────────────────
        if state == "fade_in":
            draw_fade(screen, fade_alpha, current_level, font, big_font)

        elif state == "lose":
            draw_overlay(screen, font, big_font,
                         "YOU DIED",
                         [f"Reached: {LEVEL_NAMES[current_level]}",
                          f"Gems this run: {level_score} / {total_gems}",
                          "Press R to retry this level"],
                         C_RED)

        elif state == "level_win":
            nxt = LEVEL_NAMES[current_level + 1]
            draw_overlay(screen, font, big_font,
                         "LEVEL COMPLETE!",
                         [f"Gems: {level_score} / {total_gems}   |   Total score: {total_score}",
                          f"Up next: {nxt}",
                          "N – Next level      R – Restart from Level 1"],
                         C_GOLD)

        elif state == "game_win":
            draw_overlay(screen, font, big_font,
                         "ALL LEVELS CLEARED!",
                         [f"You conquered the Forest Temple!",
                          f"Final score: {total_score} gems",
                          "Press R to play again"],
                         C_GREEN)

        pygame.display.flip()


if __name__ == "__main__":
    main()
