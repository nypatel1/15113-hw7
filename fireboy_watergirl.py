"""
================================================================================
  FIREBOY AND WATERGIRL – The Forest Temple
  A two-player cooperative 2D platformer built with Python + Pygame
================================================================================

HOW TO PLAY
-----------
  Two players share one keyboard. Each controls one character.

  Fireboy (red)   : A / D to move left/right,  W to jump
  Watergirl (blue): ← / → to move left/right,  ↑ to jump

  GOAL: Guide BOTH characters to their matching exit door at the top
        of the level. Both must enter their door to complete the level.

HAZARDS
-------
  • Lava pools  (orange) – kill Watergirl instantly, safe for Fireboy
  • Water pools (blue)   – kill Fireboy instantly,   safe for Watergirl
  • Mud pools   (green)  – slow both characters down, but harmless

GEMS
----
  • Red gems    – only Fireboy can collect them
  • Blue gems   – only Watergirl can collect them
  • Green gems  – either character can collect them

LEVEL PROGRESSION
-----------------
  Level 1 – The Antechamber  (Easy)
  Level 2 – The Lava Labyrinth (Medium)
  Level 3 – The Crystal Crucible (Hard)

KEYBOARD SHORTCUTS
------------------
  N    – Advance to the next level  (only after completing a level)
  R    – Retry the current level    (only after dying)
         OR restart from Level 1    (only after beating all levels)
  ESC  – Quit the game

REQUIREMENTS
------------
  pip install pygame
  python fireboy_watergirl.py

CODE STRUCTURE OVERVIEW
-----------------------
  1. Constants & Colors   – screen size, tile size, RGB color palette, physics values
  2. Utility Functions    – color interpolation, transparent rect drawing
  3. Particle class       – small visual effect dots (sparks, death explosions)
  4. Gem class            – collectible diamonds that bob up and down
  5. HazardPool class     – lava / water / mud pools with animated surfaces
  6. MovingPlatform class – platforms that slide back and forth on a sine wave
  7. Character class      – Fireboy and Watergirl physics, input, drawing
  8. Door class           – exit doors that animate open when a character touches them
  9. Level builder funcs  – build_level_1/2/3 define tile maps, pools, gems, doors
  10. Rendering helpers   – draw_background, draw_tiles, draw_hud, draw_overlay
  11. main()              – the game loop: event handling, update, draw
================================================================================
"""

import pygame   # The game library: window, drawing, events, timing
import sys      # Needed for sys.exit() to close the program cleanly
import math     # Used for sine waves (smooth animations, platform movement)
import random   # Used for particle randomness and animation offsets


# ==============================================================================
#  SECTION 1: CONSTANTS & CONFIGURATION
#  All the numbers that control how the game looks and feels live here.
#  Changing these is the easiest way to tweak the game without reading
#  deep into the logic.
# ==============================================================================

# ── Window & Tile Size ────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1024, 640   # Pixel dimensions of the game window
FPS           = 60          # Frames per second – how fast the game loop runs
TILE          = 32          # Each tile (floor/wall block) is 32×32 pixels.
                            # All level coordinates are given in tile units,
                            # then multiplied by TILE to get pixel positions.

# ── Color Palette (RGB tuples) ────────────────────────────────────────────────
# All colors are defined here once so we can change the look in one place.
# Format: (Red, Green, Blue) each 0–255.

C_BG          = (15, 12, 30)    # Deep dark-purple background
C_STONE       = (60, 55, 80)    # Face color of wall/floor tiles
C_STONE_DARK  = (40, 36, 58)    # Inner bevel of tiles (darker)
C_STONE_LIT   = (90, 84, 115)   # Top highlight edge of tiles (lighter)
C_LAVA        = (220, 60, 10)   # Lava pool base color
C_LAVA_GLOW   = (255, 120, 30)  # Lava surface shimmer / wave highlight
C_WATER       = (20, 100, 220)  # Water pool base color
C_WATER_GLOW  = (80, 180, 255)  # Water surface shimmer / wave highlight
C_MUD         = (90, 130, 60)   # Mud pool base color
C_FIRE_BODY   = (230, 80, 20)   # Fireboy body / torso
C_FIRE_HEAD   = (255, 130, 40)  # Fireboy head (slightly lighter)
C_WATER_BODY  = (30, 110, 230)  # Watergirl body / torso
C_WATER_HEAD  = (80, 170, 255)  # Watergirl head (slightly lighter)
C_GEM_FIRE    = (255, 60, 60)   # Red gem (Fireboy-only collectible)
C_GEM_WATER   = (60, 180, 255)  # Blue gem (Watergirl-only collectible)
C_GEM_GREEN   = (60, 220, 100)  # Green gem (either character can collect)
C_DOOR_FIRE   = (200, 50, 10)   # Fireboy's exit door
C_DOOR_WATER  = (10, 80, 200)   # Watergirl's exit door
C_PLATFORM    = (110, 100, 140) # Moving platform surface
C_WHITE       = (255, 255, 255)
C_BLACK       = (0,   0,   0)
C_GOLD        = (255, 210, 40)  # HUD score text and level-complete color
C_GREEN       = (40,  200, 80)  # Game-win overlay color
C_RED         = (200, 40,  40)  # Death overlay color

# ── Physics Constants ─────────────────────────────────────────────────────────
# These control how characters move and fall. Tweak these to change the feel.
GRAVITY    = 0.55   # Pixels per frame² added to downward velocity each frame
JUMP_POWER = -13.5  # Initial upward velocity when jumping (negative = upward)
MOVE_SPEED = 4.5    # Horizontal pixels per frame at full speed
MUD_SLOW   = 0.4    # Multiplier applied to speed when standing in mud (40%)
MAX_FALL   = 18     # Terminal velocity – fastest a character can fall


# ==============================================================================
#  SECTION 2: UTILITY FUNCTIONS
#  Small helpers used by multiple classes.
# ==============================================================================

def lerp_color(a, b, t):
    """
    Linearly interpolate between two RGB colors.

    Parameters:
        a  – starting color tuple (r, g, b)
        b  – ending color tuple   (r, g, b)
        t  – blend factor 0.0 (fully a) → 1.0 (fully b)

    Example:
        lerp_color((255,0,0), (0,0,255), 0.5)  →  (127, 0, 127)  # purple

    Used to create darker shades (e.g. leg color = body color blended with black).
    """
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_rounded_rect(surf, color, rect, r=6, alpha=None):
    """
    Draw a rectangle with rounded corners, optionally semi-transparent.

    Parameters:
        surf  – pygame Surface to draw onto
        color – RGB or RGBA tuple
        rect  – pygame.Rect defining position and size
        r     – corner radius in pixels (default 6)
        alpha – if given (0–255), draw with that transparency level.
                If None, draw fully opaque.

    The transparency trick:
        pygame.draw.rect() doesn't support alpha directly.
        We create a temporary surface with SRCALPHA (per-pixel alpha),
        draw the rect onto it, then blit (paste) it onto the main surface.
    """
    if alpha is not None:
        # Create a small surface just the size of the rectangle
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        # Draw the rounded rect onto it with the desired alpha value
        pygame.draw.rect(s, (*color[:3], alpha), s.get_rect(), border_radius=r)
        # Paste it onto the target surface at the rect's position
        surf.blit(s, rect.topleft)
    else:
        # Normal fully-opaque draw, no temp surface needed
        pygame.draw.rect(surf, color, rect, border_radius=r)


# ==============================================================================
#  SECTION 3: PARTICLE CLASS
#  Particles are tiny glowing dots used for visual effects:
#    • Dust puffs when a character jumps
#    • Motion trail behind a running character
#    • Explosion of color when a character dies
#    • Sparkle burst when collecting a gem
#
#  Each Particle lives for a fixed number of frames (its "life"), moves
#  through the air under gravity, and fades out as it ages.
# ==============================================================================

class Particle:
    def __init__(self, x, y, color, vx=None, vy=None, life=None, size=None):
        """
        Create one particle at pixel position (x, y).

        Parameters:
            x, y   – spawn position in pixels
            color  – RGB color tuple
            vx     – horizontal velocity (pixels/frame). Random if not given.
            vy     – vertical velocity (pixels/frame). Random upward if not given.
            life   – number of frames before the particle disappears. Random if not given.
            size   – radius in pixels. Random if not given.

        All parameters except x, y, color are optional; the defaults
        produce a natural-looking random burst.
        """
        self.x        = x
        self.y        = y
        self.color    = color
        # Use the provided value, or pick a random one if none was given
        self.vx       = vx   if vx   is not None else random.uniform(-2, 2)
        self.vy       = vy   if vy   is not None else random.uniform(-3, -0.5)
        self.life     = life if life is not None else random.randint(20, 45)
        self.max_life = self.life   # Remember the starting life for fade math
        self.size     = size if size is not None else random.randint(2, 5)

    def update(self):
        """
        Move the particle one frame forward.
        - Position advances by velocity.
        - vy increases (gravity pulls it down).
        - Life decreases by 1 (particle ages toward death).
        """
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.1      # Gravity pulls particles downward over time
        self.life -= 1

    def draw(self, surf):
        """
        Draw the particle as a circle that fades and shrinks as it ages.

        The fade logic:
            alpha = 255 × (remaining_life / starting_life)
            size  = max_size × (remaining_life / starting_life)

        Both approach zero as life runs out, so old particles are dim and tiny.
        We use SRCALPHA again so the circle can be semi-transparent.
        """
        alpha = int(255 * self.life / self.max_life)        # 255 when new, 0 when dead
        t     = self.life / self.max_life                   # 1.0 → 0.0 over lifetime
        size  = max(1, int(self.size * t))                  # Shrinks as particle ages
        # Create a small transparent surface just big enough for the circle
        s = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color[:3], alpha), (size, size), size)
        surf.blit(s, (int(self.x) - size, int(self.y) - size))


# ==============================================================================
#  SECTION 4: GEM CLASS
#  Gems are collectible items scattered around each level.
#  They float up and down (bobbing animation) and emit a soft glow.
#  Only the matching character can pick up each gem type:
#    "fire"  → Fireboy only
#    "water" → Watergirl only
#    "green" → either character
# ==============================================================================

class Gem:
    def __init__(self, tx, ty, kind="green"):
        """
        Create a gem at tile position (tx, ty).

        The gem is centered within its tile: the 8px offset from the tile
        corner places it nicely in the middle of the 32px tile cell.

        Parameters:
            tx, ty – tile coordinates (multiplied by TILE to get pixels)
            kind   – "fire", "water", or "green"
        """
        # Offset by 8 pixels so the gem sits centered inside its 32px tile cell
        self.rect      = pygame.Rect(tx * TILE + 8, ty * TILE + 8, 16, 16)
        self.kind      = kind
        self.collected = False   # Flips to True when picked up; stops drawing
        # Random starting phase so gems don't all bob in sync
        self.anim      = random.uniform(0, math.pi * 2)
        # Look up the right color from a dictionary
        self.color     = {"fire": C_GEM_FIRE, "water": C_GEM_WATER, "green": C_GEM_GREEN}[kind]

    def update(self):
        """Advance the bobbing animation by a small step each frame."""
        self.anim += 0.06   # Roughly one full bob cycle every ~100 frames

    def draw(self, surf):
        """
        Draw the gem as a diamond shape with a glow underneath it.
        The gem vertically bobs using sin(anim) × amplitude.
        Once collected, nothing is drawn.
        """
        if self.collected:
            return   # Don't draw gems that have already been picked up

        bob = math.sin(self.anim) * 3   # Oscillates between -3 and +3 pixels
        cx  = self.rect.centerx
        cy  = self.rect.centery + bob   # Shift center up/down with the bob

        # ── Glow ring ─────────────────────────────────────────────────────────
        # Draw a semi-transparent circle slightly larger than the gem
        glow_s = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(glow_s, (*self.color, 50), (20, 20), 18)
        surf.blit(glow_s, (cx - 20, cy - 20))

        # ── Diamond body ──────────────────────────────────────────────────────
        # Four points: top, right, bottom, left → classic diamond shape
        pts = [(cx, cy - 9), (cx + 7, cy), (cx, cy + 9), (cx - 7, cy)]
        pygame.draw.polygon(surf, self.color, pts)

        # ── Bright highlight on the top-right facet ───────────────────────────
        bright = lerp_color(self.color, C_WHITE, 0.6)   # 60% toward white
        pygame.draw.polygon(surf, bright, [(cx, cy - 9), (cx + 7, cy), (cx, cy)])


# ==============================================================================
#  SECTION 5: HAZARD POOL CLASS
#  Hazard pools are rectangular danger zones filled with lava, water, or mud.
#  They animate with a wavy surface shimmer each frame.
#
#  Death rules (checked in Character.check_hazards):
#    Lava  → kills Watergirl
#    Water → kills Fireboy
#    Mud   → slows both, kills neither
# ==============================================================================

class HazardPool:
    def __init__(self, tx, ty, tw, th, kind="lava"):
        """
        Create a hazard pool at tile position (tx, ty), spanning tw×th tiles.

        Parameters:
            tx, ty – top-left tile coordinate
            tw, th – width and height in tiles
            kind   – "lava", "water", or "mud"
        """
        self.rect = pygame.Rect(tx * TILE, ty * TILE, tw * TILE, th * TILE)
        self.kind = kind
        self.anim = 0.0   # Animation clock, increments each frame

        # Set base color and glow color based on pool type
        if kind == "lava":
            self.color, self.glow = C_LAVA,  C_LAVA_GLOW
        elif kind == "water":
            self.color, self.glow = C_WATER, C_WATER_GLOW
        else:  # mud
            self.color, self.glow = C_MUD,   (140, 180, 90)

    def update(self):
        """Advance the wave animation clock by a small increment each frame."""
        self.anim += 0.04

    def draw(self, surf):
        """
        Draw the pool as a filled rectangle with three animated wave highlights
        on the surface to suggest rippling liquid.
        """
        # ── Base fill ─────────────────────────────────────────────────────────
        pygame.draw.rect(surf, self.color, self.rect)

        # ── Wave highlights ───────────────────────────────────────────────────
        # Split the pool width into 3 thirds; draw a small glowing ellipse in
        # each third at a y position that oscillates with sin(). Each third uses
        # a slightly different phase (i × 1.2) so they don't move in lockstep.
        for i in range(3):
            wx = self.rect.x + i * self.rect.width // 3        # X: left edge of this third
            wy = self.rect.y + 4 + int(math.sin(self.anim + i * 1.2) * 3)  # Y: oscillates ±3px
            ww = self.rect.width // 3
            s  = pygame.Surface((ww, 6), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (*self.glow, 120), s.get_rect())
            surf.blit(s, (wx, wy))

        # ── Top glow line ─────────────────────────────────────────────────────
        # A bright horizontal line along the very top edge of the pool
        pygame.draw.line(surf, self.glow,
                         (self.rect.x, self.rect.y),
                         (self.rect.right, self.rect.y), 2)


# ==============================================================================
#  SECTION 6: MOVING PLATFORM CLASS
#  Moving platforms slide back and forth on a smooth sine-wave path.
#  They can move horizontally (axis="x") or vertically (axis="y").
#
#  HOW THE SINE MOVEMENT WORKS:
#    self.t goes from 0 → 1 → 0 → 1 ... bouncing at the ends.
#    offset = sin(t × π) × distance
#    sin(0) = 0, sin(π/2) = 1, sin(π) = 0
#    So the platform eases out from its origin, reaches max displacement,
#    then eases back. This gives smooth acceleration at the ends.
#
#  The `phase` parameter sets where in the cycle a platform starts,
#  so multiple platforms don't all move in the same direction at once.
# ==============================================================================

class MovingPlatform:
    def __init__(self, tx, ty, tw, axis="x", dist=4, speed=1.5, phase=0.0):
        """
        Create a moving platform.

        Parameters:
            tx, ty  – starting tile position (top-left corner)
            tw      – width of the platform in tiles (height is always TILE/2 = 16px)
            axis    – "x" moves horizontally, "y" moves vertically
            dist    – travel distance in tiles from the start position
            speed   – how fast it moves (multiplied into the dt step size)
            phase   – starting position in the 0→1 cycle (0.5 = start at mid-point)
        """
        # Platform is half a tile tall (16px) – thin enough to land on clearly
        self.rect     = pygame.Rect(tx * TILE, ty * TILE, tw * TILE, TILE // 2)
        self.origin_x = self.rect.x    # Remember starting X for offset math
        self.origin_y = self.rect.y    # Remember starting Y for offset math
        self.axis     = axis
        self.dist     = dist * TILE    # Convert tile distance to pixels
        self.t        = phase          # Current position in 0–1 sine cycle
        self.dt       = 0.018 * speed  # Step size per frame (speed control)

    def update(self):
        """
        Advance the platform one step along its sine path.
        When t reaches 0 or 1, reverse direction (bounce).
        """
        self.t += self.dt
        # Bounce: flip direction when hitting either end of the range
        if self.t > 1.0 or self.t < 0.0:
            self.dt *= -1
            self.t = max(0.0, min(1.0, self.t))   # Clamp to valid range

        # Compute pixel offset using sine curve for smooth easing
        offset = int(math.sin(self.t * math.pi) * self.dist)

        # Apply offset to the correct axis
        if self.axis == "x":
            self.rect.x = self.origin_x + offset
        else:
            self.rect.y = self.origin_y + offset

    def draw(self, surf):
        """Draw the platform with a drop shadow, surface highlight, and bolt details."""
        # ── Drop shadow (semi-transparent ellipse below the platform) ─────────
        shadow = pygame.Surface((self.rect.width, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 60), shadow.get_rect())
        surf.blit(shadow, (self.rect.x, self.rect.bottom + 2))

        # ── Platform body ─────────────────────────────────────────────────────
        pygame.draw.rect(surf, C_PLATFORM, self.rect, border_radius=4)

        # ── Top highlight stripe ──────────────────────────────────────────────
        hi = pygame.Rect(self.rect.x + 4, self.rect.y + 2, self.rect.width - 8, 3)
        pygame.draw.rect(surf, C_STONE_LIT, hi, border_radius=2)

        # ── Decorative bolts at each end ──────────────────────────────────────
        for bx in (self.rect.x + 6, self.rect.right - 10):
            pygame.draw.circle(surf, C_STONE_DARK, (bx, self.rect.centery), 3)


# ==============================================================================
#  SECTION 7: CHARACTER CLASS
#  Both Fireboy and Watergirl are instances of this single class.
#  The `kind` parameter ("fire" or "water") controls their colors,
#  which hazards kill them, and which gems they can collect.
#
#  PHYSICS MODEL (simple AABB):
#    Each frame: apply gravity → move X → resolve X collisions →
#                move Y → resolve Y collisions → clamp to screen.
#
#    AABB = Axis-Aligned Bounding Box. The character is treated as a
#    rectangle that cannot overlap with solid tiles. When overlapping
#    is detected, we push the character just outside the tile edge.
# ==============================================================================

class Character:
    W, H = 22, 30   # Width and height in pixels for both characters

    def __init__(self, x, y, kind="fire"):
        """
        Create a character at pixel position (x, y).

        Parameters:
            x, y – spawn pixel coordinates (top-left of the character rect)
            kind – "fire" (Fireboy) or "water" (Watergirl)
        """
        self.kind      = kind
        self.rect      = pygame.Rect(x, y, self.W, self.H)  # Collision hitbox
        self.vx        = 0.0        # Horizontal velocity (pixels/frame)
        self.vy        = 0.0        # Vertical velocity (pixels/frame, + = downward)
        self.on_ground = False      # True only when standing on a solid surface
        self.alive     = True       # False after touching a deadly hazard
        self.anim      = 0.0        # Walk/idle animation clock
        self.facing    = 1          # 1 = facing right, -1 = facing left
        self.in_mud    = False      # True when feet are in a mud pool
        self.particles = []         # List of active Particle effects for this character

        # Assign colors based on character type
        if kind == "fire":
            self.body_color  = C_FIRE_BODY
            self.head_color  = C_FIRE_HEAD
            self.flame_color = C_LAVA_GLOW   # Aura color for flame wisps above head
        else:
            self.body_color  = C_WATER_BODY
            self.head_color  = C_WATER_HEAD
            self.flame_color = C_WATER_GLOW  # Aura color for water droplets

    def handle_input(self, keys, left_key, right_key, jump_key):
        """
        Read the keyboard and update the character's velocity.
        Called every frame while the game is in the 'playing' state.

        Parameters:
            keys      – result of pygame.key.get_pressed() (snapshot of all keys)
            left_key  – pygame key constant for moving left  (e.g. pygame.K_a)
            right_key – pygame key constant for moving right (e.g. pygame.K_d)
            jump_key  – pygame key constant for jumping      (e.g. pygame.K_w)

        Mud slows both horizontal speed and jump height.
        """
        if not self.alive:
            return   # Dead characters ignore input

        # Mud halves the effective speed
        speed = MOVE_SPEED * (MUD_SLOW if self.in_mud else 1.0)

        if keys[left_key]:
            self.vx     = -speed
            self.facing = -1          # Character faces left
        elif keys[right_key]:
            self.vx     = speed
            self.facing = 1           # Character faces right
        else:
            # No key held: decelerate with friction (multiply by 0.75 each frame)
            # This prevents instant stopping while keeping control snappy
            self.vx *= 0.75

        # Jump only if a jump key is pressed AND the character is on solid ground
        # (prevents double-jumping in mid-air)
        if keys[jump_key] and self.on_ground:
            self.vy        = JUMP_POWER * (0.7 if self.in_mud else 1.0)
            self.on_ground = False
            # Spawn 6 small dust particles from the feet
            for _ in range(6):
                self.particles.append(
                    Particle(self.rect.centerx, self.rect.bottom,
                             self.body_color, vy=random.uniform(-1.5, -0.5))
                )

    def apply_physics(self, tiles, moving_platforms):
        """
        Apply gravity, move the character, and resolve collisions.
        Called every frame in the playing state.

        The order matters:
            1. Apply gravity to vy (cap at MAX_FALL terminal velocity)
            2. Move X, then fix any X overlaps
            3. Move Y, then fix any Y overlaps
            4. Clamp X to screen bounds (can't walk off the sides)

        Separating X and Y resolution prevents corner-catching glitches.
        """
        # Step 1: Gravity
        self.vy = min(self.vy + GRAVITY, MAX_FALL)

        # Step 2: Move and resolve horizontally
        self.rect.x += int(self.vx)
        self._resolve_x(tiles, moving_platforms)

        # Step 3: Move and resolve vertically
        self.rect.y += int(self.vy)
        self._resolve_y(tiles, moving_platforms)

        # Step 4: Keep the character inside the screen width
        self.rect.x = max(0, min(WIDTH - self.W, self.rect.x))

    def _all_rects(self, tiles, moving_platforms):
        """
        Return a combined list of all solid collision rectangles:
        static tile rects + moving platform rects.
        This is a helper used by both _resolve_x and _resolve_y.
        """
        return tiles + [p.rect for p in moving_platforms]

    def _resolve_x(self, tiles, moving_platforms):
        """
        Fix horizontal overlaps with solid surfaces.
        If the character has moved into a tile:
          - Moving right (vx > 0): push left until flush with tile's left edge
          - Moving left  (vx < 0): push right until flush with tile's right edge
        Then zero out horizontal velocity to prevent sliding through.
        """
        for r in self._all_rects(tiles, moving_platforms):
            if self.rect.colliderect(r):
                if self.vx > 0:
                    self.rect.right = r.left   # Hit a wall on the right
                elif self.vx < 0:
                    self.rect.left  = r.right  # Hit a wall on the left
                self.vx = 0

    def _resolve_y(self, tiles, moving_platforms):
        """
        Fix vertical overlaps with solid surfaces and set on_ground.
        If the character has moved into a tile:
          - Moving down (vy > 0): land on top → set on_ground = True
          - Moving up   (vy < 0): hit ceiling → bounce off bottom of tile
        on_ground is reset to False at the start of each call so it's only
        True when actively resting on a surface this exact frame.
        """
        self.on_ground = False
        for r in self._all_rects(tiles, moving_platforms):
            if self.rect.colliderect(r):
                if self.vy > 0:
                    # Falling downward: land on top of this tile
                    self.rect.bottom = r.top
                    self.vy          = 0
                    self.on_ground   = True
                elif self.vy < 0:
                    # Moving upward: hit underside of tile (ceiling)
                    self.rect.top = r.bottom
                    self.vy       = 0

    def check_hazards(self, pools):
        """
        Test whether the character's feet are touching a hazard pool.
        Called every frame in the playing state.

        Uses a thin "feet rectangle" at the bottom of the character's hitbox
        (6 pixels tall, inset 2px from the sides) to detect pool contact.
        This prevents dying from merely walking past the edge of a pool.

        Effects:
            mud  → set self.in_mud = True  (slows movement, see handle_input)
            wrong element pool → call self.die()
        """
        self.in_mud = False   # Reset each frame; will be set True below if needed
        for pool in pools:
            # Narrow contact zone at the character's feet
            feet = pygame.Rect(self.rect.x + 2, self.rect.bottom - 6, self.W - 4, 8)
            if feet.colliderect(pool.rect):
                if pool.kind == "mud":
                    self.in_mud = True   # Mud: slow down, don't die
                # Fireboy dies in water; Watergirl dies in lava
                elif (self.kind == "fire"  and pool.kind == "water") or \
                     (self.kind == "water" and pool.kind == "lava"):
                    self.die()

    def die(self):
        """
        Kill the character and spawn a burst of colorful particles.
        Sets self.alive = False, which stops input, physics, and drawing
        of the character sprite (particles continue to play out).
        The game detects death in main() and transitions to the 'lose' state.
        """
        if self.alive:   # Guard: only trigger once even if called multiple times
            self.alive = False
            for _ in range(20):
                self.particles.append(
                    Particle(self.rect.centerx, self.rect.centery,
                             self.body_color,
                             vx=random.uniform(-4, 4),      # Explode outward
                             vy=random.uniform(-6, -1),     # Mostly upward
                             life=random.randint(30, 60),
                             size=random.randint(4, 8))
                )

    def collect_gems(self, gems):
        """
        Check if this character is touching any uncollected gem it can pick up.

        Collection rules:
            Fireboy    can collect "fire" and "green" gems.
            Watergirl  can collect "water" and "green" gems.

        Returns the number of gems collected this frame (added to level score).
        Spawns a sparkle particle burst on collection.
        """
        count = 0
        for g in gems:
            if not g.collected and self.rect.colliderect(g.rect):
                # Check that this character is allowed to collect this gem type
                if (self.kind == "fire"  and g.kind in ("fire", "green")) or \
                   (self.kind == "water" and g.kind in ("water", "green")):
                    g.collected = True
                    count += 1
                    # Sparkle burst at gem position
                    for _ in range(10):
                        self.particles.append(
                            Particle(g.rect.centerx, g.rect.centery,
                                     g.color, size=4, life=25)
                        )
        return count

    def update_anim(self):
        """
        Advance the animation clock and manage the particle list.

        The anim clock drives:
          - Leg and arm swing angles in draw()
          - Water droplet orbit positions in draw()

        A motion trail particle is randomly spawned behind the character
        when running (30% chance per frame while moving).

        Dead particles (life ≤ 0) are removed from the list here.
        """
        # Advance faster while moving, slower while idle
        if abs(self.vx) > 0.5:
            self.anim += 0.18   # Running: faster swing
        else:
            self.anim += 0.05   # Idle: gentle sway

        # Randomly spawn a small trail particle while running
        if abs(self.vx) > 1 and random.random() < 0.3:
            self.particles.append(
                Particle(
                    self.rect.centerx - self.facing * 8,   # Behind the character
                    self.rect.centery + 6,
                    self.body_color, size=3, life=12
                )
            )

        # Update all particles and remove dead ones
        for p in self.particles[:]:   # Iterate on a copy so we can remove safely
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

    def draw(self, surf):
        """
        Draw the character sprite using simple pygame shapes (no image files).
        The body is made of rectangles and circles; limbs swing with sin(anim).

        Draw order (back to front):
            1. Particles (behind body)
            2. Drop shadow
            3. Body glow halo
            4. Legs
            5. Body torso
            6. Arms
            7. Head
            8. Eyes + pupils + shine
            9. Elemental aura (flames for Fireboy, droplets for Watergirl)
        """
        # Always draw particles even after death (death explosion plays out)
        for p in self.particles:
            p.draw(surf)

        if not self.alive:
            return   # Don't draw the sprite body after death

        x, y = self.rect.x, self.rect.y
        cx   = self.rect.centerx

        # Leg swing: how far each leg is offset vertically while walking
        # sin(anim) oscillates smoothly; only applied when actually moving
        leg_swing = math.sin(self.anim) * 5 if abs(self.vx) > 0.5 else 0

        # ── Drop shadow (soft ellipse below feet) ─────────────────────────────
        sh = pygame.Surface((self.W + 6, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 50), sh.get_rect())
        surf.blit(sh, (x - 3, self.rect.bottom + 1))

        # ── Body glow (soft halo around the whole character) ──────────────────
        gl = pygame.Surface((self.W + 16, self.H + 16), pygame.SRCALPHA)
        pygame.draw.ellipse(gl, (*self.body_color, 40), (0, 0, self.W + 16, self.H + 16))
        surf.blit(gl, (x - 8, y - 8))

        # ── Legs (two rectangles that swing in opposite directions) ───────────
        lc = lerp_color(self.body_color, C_BLACK, 0.3)   # Slightly darker than body
        pygame.draw.rect(surf, lc, (cx - 8, y + 18 + int(leg_swing),  7, 12), border_radius=3)
        pygame.draw.rect(surf, lc, (cx + 1, y + 18 - int(leg_swing),  7, 12), border_radius=3)
        # Note: +leg_swing on left leg, -leg_swing on right leg → opposite swing

        # ── Body torso ────────────────────────────────────────────────────────
        pygame.draw.rect(surf, self.body_color,
                         pygame.Rect(x + 1, y + 10, self.W - 2, 18), border_radius=5)

        # ── Arms (swing opposite to legs for natural walking motion) ──────────
        arm_swing = math.sin(self.anim) * 4 if abs(self.vx) > 0.5 else 0
        pygame.draw.rect(surf, lc, (x - 3,             y + 12 + int(arm_swing), 6, 10), border_radius=3)
        pygame.draw.rect(surf, lc, (self.rect.right-3, y + 12 - int(arm_swing), 6, 10), border_radius=3)

        # ── Head ──────────────────────────────────────────────────────────────
        pygame.draw.circle(surf, self.head_color, (cx, y + 8), 11)

        # ── Eyes ──────────────────────────────────────────────────────────────
        # Shift eyes horizontally based on facing direction so they look ahead
        eo = self.facing * 2   # Eye offset: slightly forward based on direction
        for ex in (cx + eo + 3, cx + eo - 3):   # Two eyes side by side
            pygame.draw.circle(surf, C_WHITE, (ex, y + 6), 4)                   # White sclera
            pygame.draw.circle(surf, C_BLACK, (ex + self.facing, y + 6), 2)     # Pupil (looks forward)
            pygame.draw.circle(surf, C_WHITE, (ex + 1, y + 5), 1)               # Shine highlight

        # ── Elemental aura ────────────────────────────────────────────────────
        if self.kind == "fire":
            # Three small random flame wisps above Fireboy's head
            for _ in range(3):
                fx = cx + random.randint(-6, 6)
                fy = y  - random.randint(2, 10)
                fs = pygame.Surface((8, 12), pygame.SRCALPHA)
                pygame.draw.ellipse(fs, (*self.flame_color, 160), fs.get_rect())
                surf.blit(fs, (fx - 4, fy - 6))
        else:
            # Two water droplets orbiting Watergirl using cos/sin for a circle path
            for i in range(2):
                dx = int(cx + math.cos(self.anim + i * 3) * 10)
                dy = int(y + 4 + math.sin(self.anim + i * 3) * 5)
                pygame.draw.circle(surf, (*self.flame_color, 130), (dx, dy), 3)


# ==============================================================================
#  SECTION 8: DOOR CLASS
#  Each level has two exit doors: one red (Fireboy) and one blue (Watergirl).
#  When the matching character stands in front of a door, it slowly animates
#  open from the bottom up. When fully open (open_anim reaches 1.0), the door
#  sets self.opened = True. The game wins when BOTH doors are opened.
# ==============================================================================

class Door:
    def __init__(self, tx, ty, kind="fire"):
        """
        Create a door at tile position (tx, ty).
        The door is 1 tile wide and 2 tiles tall, shifted up 10px so it
        sits nicely on a platform rather than being flush with the floor.

        Parameters:
            tx, ty – tile coordinates
            kind   – "fire" or "water"
        """
        # Door rect: 1 tile wide, 2 tiles tall, offset upward by 10px
        self.rect      = pygame.Rect(tx * TILE, ty * TILE - 10, TILE, TILE * 2 + 10)
        self.kind      = kind
        self.anim      = random.uniform(0, math.pi * 2)   # Glow pulse clock
        self.open_anim = 0.0    # 0.0 = fully closed, 1.0 = fully open
        self.opened    = False  # True when open_anim reaches 1.0
        self.color     = C_DOOR_FIRE if kind == "fire" else C_DOOR_WATER
        self.glow      = C_LAVA_GLOW if kind == "fire" else C_WATER_GLOW

    def update(self, character):
        """
        Animate the door based on whether the matching character is inside it.

        If the character is alive and overlapping the door rect:
            open_anim increases toward 1.0 (door slides open)
        Otherwise:
            open_anim decreases toward 0.0 (door slides closed)

        The door is only "opened" (win condition met) when open_anim == 1.0.
        This means the character must stay inside the door for a moment.

        Parameters:
            character – the Character instance for this door's element
        """
        self.anim += 0.04   # Advance the glow pulse regardless

        if character.rect.colliderect(self.rect) and character.alive:
            # Character is inside: open the door
            self.open_anim = min(1.0, self.open_anim + 0.05)
            self.opened    = self.open_anim >= 1.0
        else:
            # Character left: close the door again
            self.open_anim = max(0.0, self.open_anim - 0.05)

    def draw(self, surf):
        """
        Draw the door with:
          - A pulsing glow halo (animated with sin)
          - A stone frame and colored inner panel
          - A black void that reveals from the bottom as the door opens
          - An elemental symbol (flame for fire, droplet for water)
          - A colored outline border
        """
        r = self.rect

        # ── Pulsing glow halo ─────────────────────────────────────────────────
        gl = pygame.Surface((r.width + 20, r.height + 20), pygame.SRCALPHA)
        a  = 40 + int(20 * math.sin(self.anim))   # Alpha pulses between 20 and 60
        pygame.draw.rect(gl, (*self.glow, a), gl.get_rect(), border_radius=8)
        surf.blit(gl, (r.x - 10, r.y - 10))

        # ── Stone frame ───────────────────────────────────────────────────────
        pygame.draw.rect(surf, lerp_color(self.color, C_STONE_DARK, 0.5), r, border_radius=6)

        # ── Opening animation: black void grows from the bottom ───────────────
        if self.open_anim > 0:
            open_h = int(r.height * self.open_anim)   # How many pixels are "open"
            inner  = pygame.Rect(r.x + 4, r.bottom - open_h - 4, r.width - 8, open_h)
            s = pygame.Surface((inner.width, inner.height), pygame.SRCALPHA)
            s.fill((0, 0, 0, 200))   # Semi-transparent black "interior"
            surf.blit(s, inner.topleft)

        # ── Colored door face ─────────────────────────────────────────────────
        pygame.draw.rect(surf, self.color,
                         pygame.Rect(r.x + 4, r.y + 4, r.width - 8, r.height - 8),
                         border_radius=4)

        # ── Elemental symbol on the door face ─────────────────────────────────
        sc = r.centery
        if self.kind == "fire":
            # Flame: a pointed star-like polygon
            pygame.draw.polygon(surf, self.glow,
                [(r.centerx, sc-14), (r.centerx+8, sc), (r.centerx, sc-4),
                 (r.centerx-8, sc), (r.centerx, sc+12)])
        else:
            # Water drop: a circle for the bottom, triangle for the top
            pygame.draw.circle(surf, self.glow, (r.centerx, sc + 6), 8)
            pygame.draw.polygon(surf, self.glow,
                [(r.centerx, sc-14), (r.centerx-8, sc+2), (r.centerx+8, sc+2)])

        # ── Glowing outline border ────────────────────────────────────────────
        pygame.draw.rect(surf, self.glow, r, 2, border_radius=6)


# ==============================================================================
#  SECTION 9: LEVEL BUILDER FUNCTIONS
#
#  Each level is a Python function that returns all the objects needed:
#    tiles            – list of pygame.Rect (solid collision geometry)
#    pools            – list of HazardPool
#    moving_platforms – list of MovingPlatform
#    gems             – list of Gem
#    doors            – list of [Door (fire), Door (water)]
#    fb_pos, wg_pos   – (x, y) pixel spawn positions for each character
#
#  TILE MAP FORMAT:
#    tile_defs is a list of (tx, ty, tw, th) tuples:
#      tx, ty = top-left tile coordinate
#      tw     = width in tiles
#      th     = height in tiles
#    The helper _build_tiles() expands these into individual 32×32 Rects.
#
#  The screen is 32 tiles wide × 20 tiles tall (1024 × 640 pixels).
#  Tile (0,0) is top-left; (31,19) is bottom-right.
#  Tile row 19 = floor. Tile row 0 = ceiling. Columns 0 and 31 = walls.
# ==============================================================================

def build_level_1():
    """
    LEVEL 1 – THE ANTECHAMBER  (Difficulty: Easy)
    -----------------------------------------------
    Design goals:
      • Teach the basic mechanics without punishing new players
      • Wide platforms with plenty of room to land
      • Only 4 small hazard pools (2 lava, 2 water)
      • Only 2 moving platforms, both slow
      • Doors are close together at the center-top

    Route: Both characters climb 4 floor levels roughly symmetrically.
    The center path is mostly safe; hazards are placed at the edges.
    """
    tile_defs = [
        # ── Border walls, ceiling, floor ────────────────────────────────────
        (0,  0, 32, 1),   # Ceiling (top row)
        (0,  0,  1, 20),  # Left wall (full height)
        (31, 0,  1, 20),  # Right wall (full height)
        (0, 19, 32,  1),  # Floor (bottom row)

        # ── Ground ledges (row 15) – wide, generous ──────────────────────────
        (1,  15,  6, 1),  # Left ledge
        (13, 15,  6, 1),  # Center ledge
        (25, 15,  6, 1),  # Right ledge

        # ── Mid-level platforms (row 10) ──────────────────────────────────────
        (1,  10,  5, 1),  # Left mid
        (14, 10,  4, 1),  # Center mid
        (26, 10,  5, 1),  # Right mid
        (5,  11,  1,  4), # Left pillar (connects floor to mid)
        (26, 11,  1,  4), # Right pillar

        # ── Upper platforms (row 5) ───────────────────────────────────────────
        (1,   5,  7, 1),  # Left upper
        (13,  5,  6, 1),  # Center upper
        (24,  5,  7, 1),  # Right upper
        (7,   6,  1,  4), # Left pillar (connects mid to upper)
        (24,  6,  1,  4), # Right pillar

        # ── Top platform (row 2) – doors sit here ─────────────────────────────
        (10,  2, 12, 1),
    ]
    tiles = _build_tiles(tile_defs)

    # Four small hazard pools – easy to navigate around
    pools = [
        HazardPool(7,  17, 4, 2, "lava"),    # Large lava pit, ground level left
        HazardPool(21, 17, 4, 2, "water"),   # Large water pit, ground level right
        HazardPool(6,  11, 2, 1, "water"),   # Water on left mid (Fireboy detour)
        HazardPool(22, 11, 2, 1, "lava"),    # Lava on right mid (Watergirl detour)
    ]

    # Two slow moving platforms – introduce the mechanic gently
    moving_platforms = [
        MovingPlatform(9,  14, 3, axis="x", dist=3, speed=0.8, phase=0.0),  # Slow horizontal
        MovingPlatform(15,  8, 3, axis="y", dist=2, speed=0.7, phase=0.5),  # Slow vertical
    ]

    gems = [
        # Ground level
        Gem(2,  14, "fire"),  Gem(4,  14, "fire"),
        Gem(26, 14, "water"), Gem(28, 14, "water"),
        Gem(14, 14, "green"), Gem(17, 14, "green"),
        # Mid level
        Gem(2,   9, "fire"),  Gem(27,  9, "water"),
        Gem(16,  9, "green"),
        # Upper level
        Gem(2,   4, "fire"),  Gem(14,  4, "green"), Gem(29, 4, "water"),
        # Top platform
        Gem(12,  1, "fire"),  Gem(16,  1, "green"), Gem(20, 1, "water"),
    ]

    doors   = [Door(11, 1, "fire"), Door(19, 1, "water")]
    fb_pos  = (2  * TILE, 17 * TILE)   # Fireboy starts bottom-left
    wg_pos  = (28 * TILE, 17 * TILE)   # Watergirl starts bottom-right
    return tiles, pools, moving_platforms, gems, doors, fb_pos, wg_pos


def build_level_2():
    """
    LEVEL 2 – THE LAVA LABYRINTH  (Difficulty: Medium)
    ----------------------------------------------------
    Design goals:
      • Force characters to take completely different routes
      • A center wall divides the level into two halves
      • Left side: safer for Fireboy (mostly water hazards Watergirl must avoid)
      • Right side: safer for Watergirl (mostly lava hazards Fireboy must avoid)
      • The only crossing point is a gap in the center wall (rows 10–11)
      • Faster platforms require better timing
      • 5 moving platforms (was 2 in Level 1)

    Route: Characters split at the start, each climbs their own side, and
    cross through the center wall gap near the top.
    """
    tile_defs = [
        # ── Border ──────────────────────────────────────────────────────────
        (0,  0, 32, 1), (0, 0, 1, 20), (31, 0, 1, 20), (0, 19, 32, 1),

        # ── Ground landings ───────────────────────────────────────────────────
        (1,  16,  4, 1),   # Far left ground shelf
        (7,  17,  2, 1),   # Small step near left gap
        (11, 15,  3, 1),   # Center-left raised shelf
        (18, 15,  3, 1),   # Center-right raised shelf
        (22, 17,  2, 1),   # Small step near right gap
        (27, 16,  4, 1),   # Far right ground shelf

        # ── Center dividing wall ─────────────────────────────────────────────
        # Two sections with a gap at rows 10–11 (the only crossing point)
        (15,  4,  2,  6),  # Upper half of wall (rows 4–9)
        (15, 12,  2,  7),  # Lower half of wall (rows 12–18)

        # ── Left-side platforms ───────────────────────────────────────────────
        (1,  11,  5, 1),   # Left lower mid
        (7,   9,  4, 1),   # Left mid
        (1,   6,  6, 1),   # Left upper
        (8,   4,  4, 1),   # Left top

        # ── Right-side platforms ──────────────────────────────────────────────
        (19, 11,  5, 1),   # Right lower mid
        (21,  9,  4, 1),   # Right mid
        (19,  6,  6, 1),   # Right upper
        (21,  4,  4, 1),   # Right top

        # ── Top passages ──────────────────────────────────────────────────────
        (1,   2,  6, 1),   # Far left top (Fireboy door area)
        (11,  2,  4, 1),   # Left-center top
        (19,  2,  4, 1),   # Right-center top
        (27,  2,  4, 1),   # Far right top (Watergirl door area)
    ]
    tiles = _build_tiles(tile_defs)

    pools = [
        # ── Ground-level alternating gauntlet ─────────────────────────────────
        HazardPool(5,  17, 2, 2, "lava"),    # Lava pits at ground gaps
        HazardPool(9,  17, 2, 2, "water"),
        HazardPool(13, 17, 2, 2, "lava"),
        HazardPool(18, 17, 2, 2, "water"),
        HazardPool(24, 17, 2, 2, "lava"),

        # ── Mid-level hazards ─────────────────────────────────────────────────
        HazardPool(6,  12, 1, 1, "water"),   # Water on left mid platform
        HazardPool(11, 10, 2, 1, "lava"),    # Lava blocks left mid route
        HazardPool(21, 12, 2, 1, "water"),   # Water on right mid platform
        HazardPool(25, 10, 2, 1, "lava"),    # Lava blocks right mid route

        # ── Upper hazards ─────────────────────────────────────────────────────
        HazardPool(2,   7, 2, 1, "water"),   # Water near left upper platform
        HazardPool(23,  7, 2, 1, "lava"),    # Lava near right upper platform
        HazardPool(9,   5, 2, 1, "mud"),     # Mud slows approach to top-left
        HazardPool(23,  5, 2, 1, "mud"),     # Mud slows approach to top-right
    ]

    # Five platforms – faster and more varied than Level 1
    moving_platforms = [
        MovingPlatform(11, 13, 3, axis="x", dist=3, speed=1.2, phase=0.0),  # Left gap bridge
        MovingPlatform(18, 13, 3, axis="x", dist=3, speed=1.2, phase=0.5),  # Right gap bridge
        MovingPlatform(4,   8, 2, axis="y", dist=2, speed=1.1, phase=0.3),  # Left elevator
        MovingPlatform(27,  8, 2, axis="y", dist=2, speed=1.1, phase=0.7),  # Right elevator
        MovingPlatform(14,  7, 2, axis="y", dist=2, speed=1.4, phase=0.0),  # Center narrow gate
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


def build_level_3():
    """
    LEVEL 3 – THE CRYSTAL CRUCIBLE  (Difficulty: Hard)
    ----------------------------------------------------
    Design goals:
      • Dense alternating lava+water pools across the entire floor
      • Characters start on tiny landings – fall off and you land in a hazard
      • Every floor section has a hazard that forces one character away
      • 10 moving platforms (many fast, short, requiring precise timing)
      • Inner walls restrict routing and force specific paths
      • Mud pools placed directly before the final door – punishes rushing
      • Characters must take entirely separate routes and reunite only at the top

    Route: Characters separate at spawn, navigate independent vertical shafts
    through the level, and converge on the top-center door platform.
    """
    tile_defs = [
        # ── Border ──────────────────────────────────────────────────────────
        (0,  0, 32, 1), (0, 0, 1, 20), (31, 0, 1, 20), (0, 19, 32, 1),

        # ── Tiny starting landings ────────────────────────────────────────────
        (1,  18,  2, 1),   # Fireboy spawn (left, only 2 tiles wide)
        (29, 18,  2, 1),   # Watergirl spawn (right, only 2 tiles wide)
        (14, 17,  4, 1),   # Small center island at floor level

        # ── Lower floor platforms ─────────────────────────────────────────────
        (1,  14,  3, 1), (6,  15,  2, 1),
        (10, 13,  3, 1), (14, 14,  4, 1), (19, 13,  3, 1),
        (24, 15,  2, 1), (28, 14,  3, 1),

        # ── Mid-level platforms ───────────────────────────────────────────────
        (1,  10,  3, 1), (5,  11,  2, 1),
        (9,   9,  2, 1), (13, 10,  2, 1),
        (17, 10,  2, 1), (21,  9,  2, 1),
        (25, 11,  2, 1), (28, 10,  3, 1),

        # ── Inner routing walls (force specific paths) ────────────────────────
        (6,   5,  1,  5),  # Left inner wall (rows 5–9)
        (25,  5,  1,  5),  # Right inner wall (rows 5–9)

        # ── Upper platforms ───────────────────────────────────────────────────
        (1,   6,  4, 1), (7,   5,  3, 1),
        (12,  6,  4, 1), (16,  6,  4, 1),
        (22,  5,  3, 1), (27,  6,  4, 1),

        # ── Top level ─────────────────────────────────────────────────────────
        (1,   2,  5, 1), (9,   3,  4, 1),
        (14,  2,  4, 1),  # <-- Door platform (center-top, both doors here)
        (19,  3,  4, 1), (26,  2,  5, 1),
    ]
    tiles = _build_tiles(tile_defs)

    pools = [
        # ── Ground floor gauntlet: alternating lava/water, nearly wall-to-wall ─
        HazardPool(3,  18, 3, 1, "water"), HazardPool(6,  18, 2, 1, "lava"),
        HazardPool(8,  18, 3, 1, "water"), HazardPool(11, 18, 3, 1, "lava"),
        HazardPool(18, 18, 3, 1, "water"), HazardPool(21, 18, 3, 1, "lava"),
        HazardPool(24, 18, 3, 1, "water"), HazardPool(27, 18, 2, 1, "lava"),

        # ── Lower level hazards ───────────────────────────────────────────────
        HazardPool(4,  15, 2, 1, "water"), HazardPool(22, 15, 2, 1, "lava"),
        HazardPool(11, 14, 1, 1, "lava"),  HazardPool(20, 14, 1, 1, "water"),

        # ── Mid-level hazards ─────────────────────────────────────────────────
        HazardPool(3,  11, 2, 1, "water"), HazardPool(10, 10, 1, 1, "lava"),
        HazardPool(14, 11, 1, 1, "water"), HazardPool(17, 11, 1, 1, "lava"),
        HazardPool(21, 10, 1, 1, "water"), HazardPool(26, 11, 2, 1, "lava"),

        # ── Upper hazards ─────────────────────────────────────────────────────
        HazardPool(2,   7, 2, 1, "water"), HazardPool(8,   6, 2, 1, "lava"),
        HazardPool(13,  7, 1, 1, "water"), HazardPool(18,  7, 1, 1, "lava"),
        HazardPool(22,  6, 2, 1, "water"), HazardPool(28,  7, 2, 1, "lava"),

        # ── Mud slowdowns: right before the final climb ───────────────────────
        HazardPool(9,   4, 2, 1, "mud"),   # Left approach to top
        HazardPool(21,  4, 2, 1, "mud"),   # Right approach to top
        HazardPool(14,  3, 4, 1, "mud"),   # On the door platform itself
    ]

    # Ten moving platforms – many are fast and cover short distances
    moving_platforms = [
        # Ground crossings (fast horizontals over the death-pool gauntlet)
        MovingPlatform(3,  17, 2, axis="x", dist=4, speed=1.8, phase=0.0),
        MovingPlatform(19, 17, 2, axis="x", dist=4, speed=1.8, phase=0.5),
        # Lower verticals
        MovingPlatform(7,  14, 2, axis="y", dist=2, speed=1.4, phase=0.2),
        MovingPlatform(23, 14, 2, axis="y", dist=2, speed=1.4, phase=0.8),
        # Mid horizontals (narrow landings, tight timing required)
        MovingPlatform(11,  9, 2, axis="x", dist=2, speed=2.0, phase=0.0),
        MovingPlatform(19,  9, 2, axis="x", dist=2, speed=2.0, phase=0.5),
        # Upper fast verticals (hardest platforms in the game)
        MovingPlatform(4,   5, 2, axis="y", dist=3, speed=1.6, phase=0.0),
        MovingPlatform(26,  5, 2, axis="y", dist=3, speed=1.6, phase=0.5),
        # Top moving bridges to the door platform
        MovingPlatform(10,  2, 3, axis="x", dist=3, speed=1.5, phase=0.3),
        MovingPlatform(18,  2, 3, axis="x", dist=3, speed=1.5, phase=0.7),
    ]

    gems = [
        # Ground
        Gem(1,  17, "fire"),  Gem(29, 17, "water"),
        Gem(14, 16, "green"), Gem(17, 16, "green"),
        # Lower
        Gem(1,  13, "fire"),  Gem(11, 12, "fire"),
        Gem(29, 13, "water"), Gem(20, 12, "water"),
        Gem(15, 13, "green"),
        # Mid
        Gem(1,   9, "fire"),  Gem(9,   8, "fire"),
        Gem(29,  9, "water"), Gem(22,  8, "water"),
        Gem(14,  9, "green"), Gem(17,  9, "green"),
        # Upper
        Gem(1,   5, "fire"),  Gem(7,   4, "fire"),
        Gem(28,  5, "water"), Gem(23,  4, "water"),
        Gem(13,  5, "green"), Gem(18,  5, "green"),
        # Top
        Gem(1,   1, "fire"),  Gem(9,   2, "fire"),
        Gem(30,  1, "water"), Gem(21,  2, "water"),
        Gem(14,  1, "green"), Gem(17,  1, "green"),
    ]

    doors  = [Door(14, 1, "fire"), Door(17, 1, "water")]
    fb_pos = (1  * TILE, 17 * TILE)
    wg_pos = (29 * TILE, 17 * TILE)
    return tiles, pools, moving_platforms, gems, doors, fb_pos, wg_pos


# ==============================================================================
#  TILE BUILDER HELPER
#  Converts a compact list of (tx, ty, width, height) rectangle definitions
#  into a flat list of individual 32×32 pygame.Rect objects.
#  Used by all three level builder functions above.
# ==============================================================================

def _build_tiles(tile_defs):
    """
    Expand a list of tile rectangles into individual TILE×TILE pygame.Rects.

    Each entry in tile_defs is (tx, ty, tw, th):
        tx, ty = top-left tile coordinate
        tw     = rectangle width in tiles
        th     = rectangle height in tiles

    A (1, 5, 6, 1) entry becomes 6 individual Rect objects,
    one per tile column. This matches what the collision system expects.
    """
    tiles = []
    for (tx, ty, tw, th) in tile_defs:
        for c in range(tw):       # Each column
            for r in range(th):   # Each row
                tiles.append(pygame.Rect((tx + c) * TILE, (ty + r) * TILE, TILE, TILE))
    return tiles


# ==============================================================================
#  LEVEL REGISTRY
#  These three lists link level numbers (0, 1, 2) to their builder functions,
#  display names, and background color themes. Adding a new level is as simple
#  as writing a new build_level_N() function and appending entries here.
# ==============================================================================

LEVEL_BUILDERS = [build_level_1, build_level_2, build_level_3]

LEVEL_NAMES = [
    "Level 1 – The Antechamber",     # Easy
    "Level 2 – The Lava Labyrinth",  # Medium
    "Level 3 – The Crystal Crucible",# Hard
]

# Background color themes: (R, G, B) – each level has a distinct atmosphere
LEVEL_THEMES = [
    (20, 18, 40),  # Level 1: cool dark purple
    (35, 12,  8),  # Level 2: warm dark red (fire-themed)
    (10, 18, 42),  # Level 3: deep ocean blue (water-themed)
]


def load_level(idx):
    """
    Build and return all game objects for the given level index.
    Also creates fresh Fireboy and Watergirl instances at their spawn points.

    Parameters:
        idx – 0, 1, or 2 (index into LEVEL_BUILDERS)

    Returns:
        tiles, pools, moving_platforms, gems, doors, fireboy, watergirl
    """
    tiles, pools, moving_platforms, gems, doors, fb_pos, wg_pos = LEVEL_BUILDERS[idx]()
    fireboy   = Character(fb_pos[0], fb_pos[1], "fire")
    watergirl = Character(wg_pos[0], wg_pos[1], "water")
    return tiles, pools, moving_platforms, gems, doors, fireboy, watergirl


# ==============================================================================
#  SECTION 10: RENDERING HELPERS
#  These functions draw different parts of the game each frame.
#  They are pure drawing functions – they don't modify any game state.
# ==============================================================================

def draw_background(surf, tick, lvl):
    """
    Fill the background with a solid color, draw a subtle grid, and
    render animated torch glows at fixed positions.

    Parameters:
        surf  – the main screen Surface
        tick  – frame counter (used to animate the torch flicker)
        lvl   – current level index (selects the color theme)
    """
    # Level-specific background color
    surf.fill(LEVEL_THEMES[lvl])

    # Subtle grid lines slightly darker than the background
    gc = tuple(max(0, c - 10) for c in LEVEL_THEMES[lvl])
    for x in range(0, WIDTH, TILE):
        pygame.draw.line(surf, gc, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, TILE):
        pygame.draw.line(surf, gc, (0, y), (WIDTH, y))

    # Torches at fixed tile positions – draw a glow + stick + flame
    for tx, ty in [(4*TILE, 5*TILE), (16*TILE, 5*TILE), (28*TILE, 5*TILE),
                   (4*TILE, 11*TILE), (28*TILE, 11*TILE)]:
        # Flicker: multiply by sin(tick + offset) so each torch flickers independently
        flicker = 0.6 + 0.4 * math.sin(tick * 0.12 + tx)
        r = int(30 * flicker)
        gl = pygame.Surface((r*2, r*2), pygame.SRCALPHA)
        pygame.draw.circle(gl, (200, 120, 20, int(60 * flicker)), (r, r), r)
        surf.blit(gl, (tx - r, ty - r))         # Glow halo
        pygame.draw.rect(surf, (90, 60, 30), (tx-3, ty, 6, 14), border_radius=2)  # Wood stick
        pygame.draw.circle(surf, (230, 120, 20), (tx, ty-2), 5)                    # Orange flame
        pygame.draw.circle(surf, C_GOLD, (tx, ty-4), 3)                            # Bright tip


def draw_tiles(surf, tiles):
    """
    Draw all solid tiles with a bevel effect to give them a 3D look.
    Each tile gets:
      • A mid-tone fill (the stone face)
      • A dark inner bevel (inflate by -4px then fill darker)
      • A bright top and left edge (makes it look raised/lit from top-left)
    """
    for r in tiles:
        pygame.draw.rect(surf, C_STONE, r)                    # Stone face
        pygame.draw.rect(surf, C_STONE_DARK, r.inflate(-4, -4))  # Dark bevel inset
        pygame.draw.line(surf, C_STONE_LIT, r.topleft, r.topright)    # Top highlight
        pygame.draw.line(surf, C_STONE_LIT, r.topleft, r.bottomleft)  # Left highlight


def draw_hud(surf, lvl, level_score, total_gems, fb_alive, wg_alive,
             total_score, font, small_font, tick):
    """
    Draw the heads-up display bar at the top of the screen.
    Shows: Fireboy status (left), level info + gem count (center), Watergirl status (right).
    Dead characters show a red X over their icon.

    Parameters:
        surf        – main screen surface
        lvl         – current level index (for name display)
        level_score – gems collected this level so far
        total_gems  – total gems in this level
        fb_alive    – bool: is Fireboy alive?
        wg_alive    – bool: is Watergirl alive?
        total_score – cumulative gems across all completed levels
        font        – main HUD font
        small_font  – smaller font for control hints
        tick        – frame counter (animates the gem icon)
    """
    # Semi-transparent bar background
    hud = pygame.Surface((WIDTH, 44), pygame.SRCALPHA)
    hud.fill((10, 8, 22, 215))
    surf.blit(hud, (0, 0))

    # ── Fireboy icon (left side) ──────────────────────────────────────────────
    fb_col = C_FIRE_HEAD if fb_alive else C_RED
    pygame.draw.circle(surf, fb_col, (22, 22), 14)
    pygame.draw.circle(surf, C_FIRE_BODY, (22, 22), 14, 2)
    if not fb_alive:
        # Red X drawn over dead character
        pygame.draw.line(surf, C_RED, (15,15),(29,29),3)
        pygame.draw.line(surf, C_RED, (29,15),(15,29),3)
    surf.blit(small_font.render("FIREBOY  WASD", True, fb_col), (42, 13))

    # ── Watergirl icon (right side) ───────────────────────────────────────────
    wg_col = C_WATER_HEAD if wg_alive else C_RED
    pygame.draw.circle(surf, wg_col, (WIDTH-22, 22), 14)
    pygame.draw.circle(surf, C_WATER_BODY, (WIDTH-22, 22), 14, 2)
    if not wg_alive:
        pygame.draw.line(surf, C_RED, (WIDTH-29,15),(WIDTH-15,29),3)
        pygame.draw.line(surf, C_RED, (WIDTH-15,15),(WIDTH-29,29),3)
    wt = small_font.render("ARROW KEYS  WATERGIRL", True, wg_col)
    surf.blit(wt, wt.get_rect(right=WIDTH-42, centery=22))

    # ── Center: animated gem icon + score label ───────────────────────────────
    anim = math.sin(tick * 0.08) * 2   # Gem icon bobs gently
    pts  = [(WIDTH//2-32, int(22-10+anim)), (WIDTH//2-25, int(22+anim)),
            (WIDTH//2-32, int(22+10+anim)), (WIDTH//2-39, int(22+anim))]
    pygame.draw.polygon(surf, C_GEM_GREEN, pts)

    label = f"{LEVEL_NAMES[lvl]}   {level_score}/{total_gems}  |  Total: {total_score}"
    ct = font.render(label, True, C_GOLD)
    surf.blit(ct, ct.get_rect(centerx=WIDTH//2 + 12, centery=22))


def draw_overlay(surf, font, big_font, title, lines, color):
    """
    Draw a centered semi-transparent panel with a title and subtitle lines.
    Used for: level complete, death screen, game win screen.

    Parameters:
        surf     – main screen surface
        font     – font for subtitle lines
        big_font – font for the title
        title    – large title string (e.g. "LEVEL COMPLETE!")
        lines    – list of subtitle strings (drawn below the title)
        color    – accent color for the title and panel border
    """
    # Darken the whole screen
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 175))
    surf.blit(ov, (0, 0))

    # Centered panel
    panel = pygame.Rect(WIDTH//2 - 310, HEIGHT//2 - 120, 620, 240)
    draw_rounded_rect(surf, (20, 16, 40), panel, r=16)          # Dark fill
    pygame.draw.rect(surf, color, panel, 3, border_radius=16)   # Colored border

    # Title
    t1 = big_font.render(title, True, color)
    surf.blit(t1, t1.get_rect(centerx=WIDTH//2, centery=HEIGHT//2 - 55))

    # Subtitle lines (stacked with 30px spacing)
    for i, line in enumerate(lines):
        t = font.render(line, True, C_WHITE)
        surf.blit(t, t.get_rect(centerx=WIDTH//2, centery=HEIGHT//2 + 5 + i * 30))


def draw_fade(surf, alpha, lvl, font, big_font):
    """
    Draw the level transition fade: a black overlay that fades from opaque to
    transparent at the start of each level. While mostly opaque, the level
    name and a hint are displayed to prepare the player.

    Parameters:
        surf     – main screen surface
        alpha    – current overlay opacity (255 = black, 0 = transparent)
        lvl      – current level index (for the name display)
        font     – small font for the hint text
        big_font – large font for the level name
    """
    ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    ov.fill((0, 0, 0, int(alpha)))
    surf.blit(ov, (0, 0))

    # Only show the text when the screen is mostly dark (alpha > 120)
    # so it fades in and out with the overlay
    if alpha > 120:
        # Scale text alpha: goes from 0 at alpha=120 to 255 at alpha=255
        ta = max(0, min(255, int((alpha - 120) * 2.1)))
        t1 = big_font.render(LEVEL_NAMES[lvl], True, C_GOLD)
        t2 = font.render("Get ready – both heroes must reach their door!", True, C_WHITE)
        t1.set_alpha(ta)
        t2.set_alpha(ta)
        surf.blit(t1, t1.get_rect(centerx=WIDTH//2, centery=HEIGHT//2 - 30))
        surf.blit(t2, t2.get_rect(centerx=WIDTH//2, centery=HEIGHT//2 + 25))


# ==============================================================================
#  SECTION 11: MAIN GAME LOOP
#
#  The game loop runs at 60 FPS. Each iteration ("frame") does three things:
#    1. EVENT HANDLING  – read keyboard/window events, react to key presses
#    2. UPDATE          – advance physics, animations, check collisions
#    3. DRAW            – render everything to the screen
#
#  GAME STATES:
#    "fade_in"   – level is loading; screen fades from black with level name shown
#    "playing"   – normal gameplay; both characters active
#    "lose"      – one or both characters died; overlay shown; press R to retry
#    "level_win" – both doors opened; overlay shown; press N for next / R to restart all
#    "game_win"  – all 3 levels beaten; final score shown; press R to play again
#
#  State transitions:
#    fade_in   → playing     (when fade_alpha reaches 0)
#    playing   → lose        (when any character dies)
#    playing   → level_win   (when both doors fully open; not the last level)
#    playing   → game_win    (when both doors open on the last level)
#    lose      → fade_in     (on R key: restart current level)
#    level_win → fade_in     (on N key: load next level)
#    level_win → fade_in     (on R key: reset to level 1)
#    game_win  → fade_in     (on R key: reset to level 1)
# ==============================================================================

def main():
    # ── Pygame initialization ─────────────────────────────────────────────────
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Fireboy & Watergirl – The Forest Temple")
    clock  = pygame.time.Clock()   # Used to cap the frame rate at FPS

    # ── Font loading ──────────────────────────────────────────────────────────
    # Try to use Segoe UI (looks nice on Windows/Mac); fall back to pygame default
    try:
        font       = pygame.font.SysFont("segoeui", 18, bold=True)
        big_font   = pygame.font.SysFont("segoeui", 46, bold=True)
        small_font = pygame.font.SysFont("segoeui", 15)
    except Exception:
        font       = pygame.font.Font(None, 22)
        big_font   = pygame.font.Font(None, 54)
        small_font = pygame.font.Font(None, 18)

    # ── Initial game state ────────────────────────────────────────────────────
    current_level = 0     # Which level we're on (0 = Level 1)
    total_score   = 0     # Cumulative gem count across all levels

    # Load the first level and create character objects
    tiles, pools, moving_platforms, gems, doors, fireboy, watergirl = load_level(current_level)
    total_gems   = len(gems)   # Total gems available in this level
    level_score  = 0           # Gems collected so far this level

    tick         = 0           # Frame counter; used for animation timing
    state        = "fade_in"   # Start with the fade-in transition
    fade_alpha   = 255.0       # Start fully black, decrease to 0
    bg_particles = []          # Ambient background sparkle particles (global list)

    # ── Helper: restart the current level ────────────────────────────────────
    def restart_level():
        """
        Reload all game objects for the current level.
        Resets level_score to 0 but keeps total_score intact.
        Used when pressing R after dying.
        """
        nonlocal tiles, pools, moving_platforms, gems, doors, fireboy, watergirl
        nonlocal total_gems, level_score, state, fade_alpha, tick
        tiles, pools, moving_platforms, gems, doors, fireboy, watergirl = load_level(current_level)
        total_gems  = len(gems)
        level_score = 0
        state       = "fade_in"
        fade_alpha  = 255.0
        tick        = 0

    # ── Helper: advance to the next level ────────────────────────────────────
    def next_level():
        """
        Increment current_level and load the new level's objects.
        total_score was already updated in main() when the level was won.
        """
        nonlocal current_level, tiles, pools, moving_platforms, gems, doors
        nonlocal fireboy, watergirl, total_gems, level_score, state, fade_alpha, tick
        current_level += 1
        tiles, pools, moving_platforms, gems, doors, fireboy, watergirl = load_level(current_level)
        total_gems  = len(gems)
        level_score = 0
        state       = "fade_in"
        fade_alpha  = 255.0
        tick        = 0

    # ═════════════════════════════════════════════════════════════════════════
    #  MAIN LOOP
    # ═════════════════════════════════════════════════════════════════════════
    while True:
        clock.tick(FPS)   # Block until 1/60th of a second has passed
        tick += 1

        # ── 1. EVENT HANDLING ─────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

                # State-specific key responses
                if state == "lose":
                    if event.key == pygame.K_r:
                        restart_level()   # Retry this level

                elif state == "level_win":
                    if event.key == pygame.K_n:
                        next_level()      # Go to next level
                    elif event.key == pygame.K_r:
                        current_level = 0
                        total_score   = 0
                        restart_level()   # Full restart from Level 1

                elif state == "game_win":
                    if event.key == pygame.K_r:
                        current_level = 0
                        total_score   = 0
                        restart_level()   # Play again from the beginning

        # Snapshot of all currently held keys (used by Character.handle_input)
        keys = pygame.key.get_pressed()

        # ── 2. UPDATE ─────────────────────────────────────────────────────────

        # Fade-in transition: decrease opacity until screen is fully visible
        if state == "fade_in":
            fade_alpha -= 5.0            # Decrease by 5 per frame (255/5 = 51 frames ≈ 0.85s)
            if fade_alpha <= 0:
                fade_alpha = 0
                state = "playing"        # Transition to gameplay once fade is done

        # Main gameplay update
        if state == "playing":
            # Read keyboard input for both characters
            fireboy.handle_input(keys, pygame.K_a, pygame.K_d, pygame.K_w)
            watergirl.handle_input(keys, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP)

            # Apply gravity and resolve collisions
            fireboy.apply_physics(tiles, moving_platforms)
            watergirl.apply_physics(tiles, moving_platforms)

            # Check if feet are in any hazard pools
            fireboy.check_hazards(pools)
            watergirl.check_hazards(pools)

            # Animate all moving platforms
            for mp in moving_platforms:
                mp.update()

            # Check for gem pickups; add any collected gems to the level score
            level_score += fireboy.collect_gems(gems)
            level_score += watergirl.collect_gems(gems)

            # Update each door with its matching character (detects if they're inside)
            doors[0].update(fireboy)     # doors[0] is always the fire door
            doors[1].update(watergirl)   # doors[1] is always the water door

            # Advance animation clocks and update particles
            fireboy.update_anim()
            watergirl.update_anim()

            # Update gem bob animations
            for g in gems:
                g.update()

            # Update pool wave animations
            for p in pools:
                p.update()

            # Instant-kill if a character falls below the bottom of the screen
            for ch in (fireboy, watergirl):
                if ch.rect.top > HEIGHT and ch.alive:
                    ch.die()

            # ── Win/lose condition checks ─────────────────────────────────────
            if not fireboy.alive or not watergirl.alive:
                state = "lose"   # Either character died → game over for this level

            if doors[0].opened and doors[1].opened:
                # Both characters successfully entered their doors
                total_score += level_score   # Bank this level's gems into total
                if current_level >= len(LEVEL_BUILDERS) - 1:
                    state = "game_win"   # Last level beaten: show final screen
                else:
                    state = "level_win"  # More levels remain: show level-clear screen

        # ── Ambient background sparkle particles ──────────────────────────────
        # Every 8 frames, spawn a small rising particle at a random X position
        if tick % 8 == 0:
            bg_particles.append(
                Particle(random.randint(TILE, WIDTH - TILE), HEIGHT - TILE,
                         random.choice([C_LAVA_GLOW, C_WATER_GLOW]),
                         vy=random.uniform(-1.5, -0.4),     # Rise upward
                         life=random.randint(60, 120),
                         size=random.randint(1, 3))
            )
        # Update and prune dead ambient particles
        for p in bg_particles[:]:
            p.update()
            if p.life <= 0:
                bg_particles.remove(p)

        # ── 3. DRAW ───────────────────────────────────────────────────────────
        # Draw order: background → ambient particles → tiles → pools →
        #             moving platforms → gems → doors → characters → HUD → overlays
        # Each layer paints on top of the previous.

        draw_background(screen, tick, current_level)

        for p in bg_particles:
            p.draw(screen)

        draw_tiles(screen, tiles)

        for pool in pools:
            pool.draw(screen)

        for mp in moving_platforms:
            mp.draw(screen)

        for g in gems:
            g.draw(screen)

        for d in doors:
            d.draw(screen)

        fireboy.draw(screen)
        watergirl.draw(screen)

        draw_hud(screen, current_level, level_score, total_gems,
                 fireboy.alive, watergirl.alive, total_score, font, small_font, tick)

        # ── Overlays (drawn last, on top of everything) ───────────────────────
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
                         ["You conquered the Forest Temple!",
                          f"Final score: {total_score} gems",
                          "Press R to play again"],
                         C_GREEN)

        # Push the completed frame to the screen
        pygame.display.flip()


# ── Entry point ───────────────────────────────────────────────────────────────
# This ensures main() only runs when the file is executed directly,
# not when it's imported as a module.
if __name__ == "__main__":
    main()
