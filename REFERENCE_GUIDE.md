# Fireboy & Watergirl – Code Reference Guide

> **Who this is for:** Anyone reading the code for the first time.  
> No prior game-development experience required.

---

## Table of Contents

1. [How to Run](#1-how-to-run)
2. [Big Picture – How the Code is Organised](#2-big-picture)
3. [Key Concepts You Need to Know](#3-key-concepts)
4. [Constants & Configuration](#4-constants--configuration)
5. [Classes](#5-classes)
   - [Particle](#particle)
   - [Gem](#gem)
   - [HazardPool](#hazardpool)
   - [MovingPlatform](#movingplatform)
   - [Character](#character)
   - [Door](#door)
6. [Level Builder Functions](#6-level-builder-functions)
7. [Rendering Functions](#7-rendering-functions)
8. [The Game Loop (`main`)](#8-the-game-loop-main)
9. [Game State Machine](#9-game-state-machine)
10. [How to Modify the Game](#10-how-to-modify-the-game)

---

## 1. How to Run

```bash
pip install pygame
python fireboy_watergirl.py
```

**Controls:**

| Player | Move Left | Move Right | Jump |
|--------|-----------|------------|------|
| Fireboy (red) | `A` | `D` | `W` |
| Watergirl (blue) | `←` | `→` | `↑` |

**Other keys:** `N` = next level · `R` = retry/restart · `ESC` = quit

---

## 2. Big Picture

The file is one self-contained Python script (~930 lines). Here is how it is laid out, top to bottom:

```
fireboy_watergirl.py
│
├── imports                  (pygame, sys, math, random)
├── CONSTANTS                (screen size, colors, physics numbers)
├── Utility functions        (lerp_color, draw_rounded_rect)
│
├── class Particle           (tiny visual effect dot)
├── class Gem                (collectible diamond)
├── class HazardPool         (lava / water / mud zone)
├── class MovingPlatform     (sliding platform)
├── class Character          (Fireboy and Watergirl share this)
├── class Door               (exit door)
│
├── build_level_1()          (Easy level data)
├── build_level_2()          (Medium level data)
├── build_level_3()          (Hard level data)
├── _build_tiles()           (helper: expands tile rectangles)
│
├── LEVEL_BUILDERS / NAMES / THEMES   (level registry lists)
├── load_level()             (instantiates a level + characters)
│
├── draw_background()        (background + torch glows)
├── draw_tiles()             (stone wall/floor tiles)
├── draw_hud()               (top status bar)
├── draw_overlay()           (win/lose/transition panel)
├── draw_fade()              (fade-to-black transition)
│
└── main()                   (game loop: events → update → draw)
```

Every frame the program runs `main()`'s loop which does:
1. **Events** – Was a key pressed? Did the window close?
2. **Update** – Move characters, animate platforms, check collisions
3. **Draw** – Paint everything onto the screen, then flip (show it)

---

## 3. Key Concepts

### Tiles
The screen is divided into a **32×20 grid of 32-pixel tiles**. Level geometry (floors, walls, platforms) is described in tile coordinates `(tx, ty)` and converted to pixels by multiplying by `TILE` (32).

```
Tile (0,0) = pixel (0,0)      ← top-left corner
Tile (31,19) = pixel (992,608) ← bottom-right corner
Tile row 19 = the floor
Tile col 0 / 31 = the walls
```

### AABB Collision
Characters are rectangles. When a character moves into a tile, the code detects the overlap and pushes the character back out. This is called **AABB (Axis-Aligned Bounding Box)** collision. X and Y are resolved separately to avoid corner-snag glitches.

### The Animation Clock (`anim`)
Most animated things (characters walking, gems bobbing, door glowing) use a `self.anim` counter that increments each frame. Plugging it into `math.sin(anim)` gives a smooth oscillation between -1 and +1, which drives the animation offset.

### Particles
Particles are small circles that move, fade, shrink, and die after a fixed number of frames. They're used for jump dust, running trails, gem sparkles, and death explosions. Each `Character` owns a list of its own particles.

### Game States
The game is always in exactly one **state** (a string). The state controls what gets updated, what gets drawn, and what key presses do. See [Section 9](#9-game-state-machine) for the full diagram.

---

## 4. Constants & Configuration

All tweakable values live at the top of the file. You don't need to read any class to change how the game feels.

### Screen & Grid
| Constant | Value | Meaning |
|----------|-------|---------|
| `WIDTH`  | 1024 | Window width in pixels |
| `HEIGHT` | 640  | Window height in pixels |
| `FPS`    | 60   | Target frames per second |
| `TILE`   | 32   | Size of one tile in pixels |

### Physics
| Constant | Value | Meaning |
|----------|-------|---------|
| `GRAVITY` | 0.55 | Added to `vy` each frame (downward pull) |
| `JUMP_POWER` | -13.5 | Initial upward velocity on jump (negative = up) |
| `MOVE_SPEED` | 4.5 | Horizontal pixels/frame at full speed |
| `MUD_SLOW` | 0.4 | Speed multiplier in mud (40% of normal) |
| `MAX_FALL` | 18 | Maximum falling speed (terminal velocity) |

**How to make the game feel different:**
- **Floatier jumps:** lower `GRAVITY` (e.g. `0.35`) and raise `JUMP_POWER` (e.g. `-16`)
- **Faster characters:** raise `MOVE_SPEED` (e.g. `6.0`)
- **Slippery floor:** lower the friction multiplier in `handle_input` from `0.75` to `0.9`

### Colors
All colors are `(R, G, B)` tuples named with the prefix `C_`. Change them here to retheme the entire game without touching any drawing code.

---

## 5. Classes

### `Particle`

A single animated dot used for visual effects.

**Key attributes:**
| Attribute | Type | Description |
|-----------|------|-------------|
| `x`, `y` | float | Current position |
| `vx`, `vy` | float | Velocity per frame |
| `life` | int | Frames remaining before death |
| `max_life` | int | Starting life (used to calculate fade) |
| `size` | int | Maximum radius in pixels |
| `color` | tuple | RGB color |

**Methods:**
- `update()` – Move by velocity, apply gravity (`vy += 0.1`), decrement life
- `draw(surf)` – Draw a circle that fades and shrinks proportional to `life/max_life`

**Where particles come from:**
- Jump: 6 dust particles from feet
- Running: 30% chance of 1 trail particle per frame
- Death: 20 explosion particles
- Gem pickup: 10 sparkle particles

---

### `Gem`

A collectible diamond that bobs up and down.

**Constructor:** `Gem(tx, ty, kind)`
- `tx`, `ty` – tile coordinates (centered in tile by +8px offset)
- `kind` – `"fire"` (Fireboy only) · `"water"` (Watergirl only) · `"green"` (either)

**Key attributes:**
| Attribute | Description |
|-----------|-------------|
| `rect` | Collision rectangle (16×16 px) |
| `collected` | `True` once picked up; stops drawing and collision |
| `anim` | Bob animation clock |
| `color` | RGB color looked up from `kind` |

**Collection rules (enforced in `Character.collect_gems`):**
```
Fireboy   can collect: "fire", "green"
Watergirl can collect: "water", "green"
```

---

### `HazardPool`

A rectangular danger zone filled with lava, water, or mud.

**Constructor:** `HazardPool(tx, ty, tw, th, kind)`
- `tx`, `ty` – top-left tile position
- `tw`, `th` – width and height in tiles
- `kind` – `"lava"`, `"water"`, or `"mud"`

**Death rules:**
```
Lava  → kills Watergirl  (safe for Fireboy)
Water → kills Fireboy    (safe for Watergirl)
Mud   → slows both, kills neither
```

Death is detected in `Character.check_hazards()` using a thin "feet rectangle" at the bottom of the character's hitbox, so you have to step *into* the pool, not just walk past the edge.

---

### `MovingPlatform`

A platform that slides back and forth on a smooth sine-wave path.

**Constructor:** `MovingPlatform(tx, ty, tw, axis, dist, speed, phase)`

| Parameter | Description |
|-----------|-------------|
| `tx`, `ty` | Starting tile position |
| `tw` | Width in tiles (height is always 16px / half a tile) |
| `axis` | `"x"` = horizontal movement · `"y"` = vertical movement |
| `dist` | Travel distance in tiles from the start position |
| `speed` | How fast it moves (multiplier on the step size) |
| `phase` | Starting offset in the 0→1 cycle (use different values to desynchronise platforms) |

**How the movement works:**

```
self.t bounces between 0.0 and 1.0 each frame.
offset = sin(t × π) × (dist × TILE pixels)

sin(0)   = 0   → at origin
sin(π/2) = 1   → at maximum displacement  
sin(π)   = 0   → back at origin
```

This gives smooth acceleration at the ends (easing) rather than constant-speed back-and-forth. The `phase` parameter lets different platforms start at different points in the cycle.

---

### `Character`

Both Fireboy and Watergirl are instances of this single class. The `kind` parameter (`"fire"` or `"water"`) controls colors, hazard vulnerability, and gem compatibility.

**Hitbox:** 22 × 30 pixels

**Key attributes:**
| Attribute | Description |
|-----------|-------------|
| `kind` | `"fire"` or `"water"` |
| `rect` | Collision hitbox (pygame.Rect) |
| `vx`, `vy` | Velocity (pixels/frame) |
| `on_ground` | `True` only when resting on a surface |
| `alive` | `False` after touching a deadly hazard |
| `anim` | Walk/idle animation clock |
| `facing` | `1` = right, `-1` = left |
| `in_mud` | `True` when feet are in a mud pool |
| `particles` | List of owned Particle objects |

**Public methods:**

| Method | Called when | Purpose |
|--------|-------------|---------|
| `handle_input(keys, left, right, jump)` | Every frame | Read keyboard; set `vx`, `vy` |
| `apply_physics(tiles, platforms)` | Every frame | Gravity + collision resolution |
| `check_hazards(pools)` | Every frame | Die or slow down if in a pool |
| `collect_gems(gems)` | Every frame | Pick up gems; return count |
| `update_anim()` | Every frame | Advance anim clock; manage particles |
| `draw(surf)` | Every frame | Render sprite and particles |
| `die()` | On hazard contact | Set `alive=False`; spawn explosion |

**Physics flow (happens inside `apply_physics`):**
```
1. vy += GRAVITY          (pull down)
2. vy = min(vy, MAX_FALL) (cap speed)
3. rect.x += vx           (move horizontally)
4. resolve X collisions   (push out of walls)
5. rect.y += vy           (move vertically)
6. resolve Y collisions   (land on floors / hit ceilings)
7. clamp rect.x to screen (can't walk off sides)
```

**Collision resolution (AABB):**
```
X overlap:
  Moving right → push left until flush with tile's left edge
  Moving left  → push right until flush with tile's right edge

Y overlap (falling down) → sit on top of tile; set on_ground = True
Y overlap (moving up)    → bump off bottom of tile
```

---

### `Door`

An exit door that animates open when the matching character stands in it.

**Constructor:** `Door(tx, ty, kind)` – `kind` is `"fire"` or `"water"`

**Key attributes:**
| Attribute | Description |
|-----------|-------------|
| `open_anim` | Float 0.0–1.0 (how open the door is) |
| `opened` | `True` when `open_anim` reaches 1.0 |

**Win condition:** The game checks `doors[0].opened and doors[1].opened` every frame. Both must be simultaneously open.

**Animation:** `open_anim` increases by 0.05/frame while the character is inside, and decreases by 0.05/frame when they leave. The character must stay inside for 20 frames (1/3 second) for the door to fully open.

---

## 6. Level Builder Functions

Each level is a function: `build_level_1()`, `build_level_2()`, `build_level_3()`.

**They all return the same tuple:**
```python
tiles, pools, moving_platforms, gems, doors, fb_pos, wg_pos
```

| Return value | Type | Description |
|--------------|------|-------------|
| `tiles` | `list[pygame.Rect]` | All solid collision rectangles |
| `pools` | `list[HazardPool]` | All hazard zones |
| `moving_platforms` | `list[MovingPlatform]` | All moving platforms |
| `gems` | `list[Gem]` | All collectible gems |
| `doors` | `list[Door]` | Always `[fire_door, water_door]` |
| `fb_pos` | `(x, y)` | Fireboy pixel spawn position |
| `wg_pos` | `(x, y)` | Watergirl pixel spawn position |

### Tile map format

Inside each builder, the level geometry is written as a compact list of rectangle definitions:

```python
tile_defs = [
    (tx, ty, width_in_tiles, height_in_tiles),
    ...
]
```

The helper `_build_tiles(tile_defs)` expands these into individual 32×32 `pygame.Rect` objects. A single entry like `(1, 15, 6, 1)` becomes 6 Rects side by side.

### Level difficulty comparison

| Feature | Level 1 | Level 2 | Level 3 |
|---------|---------|---------|---------|
| Hazard pools | 4 (small) | 13 | 27 |
| Moving platforms | 2 | 5 | 10 |
| Platform speed | 0.7–0.8 | 1.1–1.4 | 1.5–2.0 |
| Spawn landing width | 6 tiles | 4 tiles | 2 tiles |
| Forced separate routes | No | Partial | Yes |
| Mud pools | 0 | 2 | 3 |

---

## 7. Rendering Functions

These are standalone functions (not methods) that draw parts of the screen each frame. They **never change game state** — they only draw.

| Function | What it draws |
|----------|---------------|
| `draw_background(surf, tick, lvl)` | Background color, grid lines, animated torch glows |
| `draw_tiles(surf, tiles)` | Stone blocks with 3D bevel effect |
| `draw_hud(...)` | Top bar: character icons, level name, gem count, total score |
| `draw_overlay(surf, font, big_font, title, lines, color)` | Centered panel for win/lose/transition screens |
| `draw_fade(surf, alpha, lvl, font, big_font)` | Black overlay + level name for fade-in transition |

### Drawing order (back to front)

Every frame, things are drawn in this order so each layer appears on top of the previous:

```
1. Background (solid color + grid + torches)
2. Ambient background particles (rising sparkles)
3. Tiles (floors and walls)
4. Hazard pools (lava, water, mud)
5. Moving platforms
6. Gems
7. Doors
8. Characters (Fireboy, Watergirl)
9. HUD (always on top of game world)
10. Overlay (fade / win / lose — covers everything)
```

---

## 8. The Game Loop (`main`)

`main()` contains the entire runtime loop. Here is what happens every frame:

```
clock.tick(FPS)           ← wait until 1/60s has passed

┌─ EVENT HANDLING ──────────────────────────────────────┐
│  pygame.QUIT → exit                                   │
│  ESC         → exit                                   │
│  R / N keys  → restart_level() or next_level()        │
│                (only when in "lose" / "level_win" /   │
│                "game_win" states)                     │
└───────────────────────────────────────────────────────┘

┌─ UPDATE ──────────────────────────────────────────────┐
│  if state == "fade_in":                               │
│      fade_alpha -= 5  →  state = "playing" at 0      │
│                                                       │
│  if state == "playing":                               │
│      character.handle_input()                         │
│      character.apply_physics()                        │
│      character.check_hazards()                        │
│      moving_platform.update()                         │
│      character.collect_gems()                         │
│      door.update(character)                           │
│      character.update_anim()                          │
│      gem.update() / pool.update()                     │
│      check fall-off-screen deaths                     │
│      check win/lose conditions                        │
│                                                       │
│  ambient particles: spawn + update + prune            │
└───────────────────────────────────────────────────────┘

┌─ DRAW ────────────────────────────────────────────────┐
│  draw_background()                                    │
│  ambient particles                                    │
│  draw_tiles()                                         │
│  pools / platforms / gems / doors / characters        │
│  draw_hud()                                           │
│  draw overlay for current state (if any)              │
│  pygame.display.flip()   ← push frame to screen      │
└───────────────────────────────────────────────────────┘
```

Two helper functions are defined **inside** `main()` because they need to update several of its local variables:
- `restart_level()` – reloads the current level, resets `level_score`
- `next_level()` – increments `current_level`, loads new level data

---

## 9. Game State Machine

The `state` variable is a string that controls the entire program flow. Here is every possible state and how transitions happen:

```
                    ┌─────────────────────────────────────────────────────┐
                    │                                                     │
            start   ▼                                                     │
          ┌──────────────┐  fade_alpha → 0                               │
          │   "fade_in"  │──────────────────► "playing"                  │
          └──────────────┘                       │                       │
                 ▲                               │                       │
                 │ R (retry)         either      │ both doors            │
          ┌──────┴───────┐        char dies      │ opened                │
          │    "lose"    │◄────────────────── ───┤                       │
          └──────────────┘                       │ not last level        │
                                          ┌──────▼──────────┐           │
                                          │  "level_win"    │  N key    │
                                          └─────────────────┘──────────►│
                                                  │                     │
                                                  │ R key               │
                                          ┌───────▼─────────┐          │
                                          │    reset to      │──────────►│
                                          │    level 1       │
                                          └─────────────────┘
                                                  
                                          last level doors opened
                                                  │
                                          ┌───────▼─────────┐
                                          │   "game_win"    │── R key ──►│
                                          └─────────────────┘            │
                                                                          │
                                          ◄─────────────────────────────-┘
                                          (restart_level() with current_level=0)
```

---

## 10. How to Modify the Game

### Change a level's difficulty

Open `build_level_2()` (or any builder). You can:

- **Add or move a platform** by editing `tile_defs`:
  ```python
  # (tile_x, tile_y, width, height)
  (10, 12, 4, 1)   # 4-tile-wide platform at row 12
  ```

- **Add a hazard pool:**
  ```python
  HazardPool(10, 13, 3, 1, "lava")  # 3-wide lava pool
  ```

- **Add a moving platform:**
  ```python
  MovingPlatform(10, 11, 3, axis="x", dist=4, speed=1.5, phase=0.0)
  ```

- **Add a gem:**
  ```python
  Gem(12, 10, "green")   # Green gem at tile (12, 10)
  ```

### Add a 4th level

1. Write a new function:
   ```python
   def build_level_4():
       tile_defs = [ ... ]
       tiles = _build_tiles(tile_defs)
       pools = [ ... ]
       moving_platforms = [ ... ]
       gems = [ ... ]
       doors = [Door(tx, ty, "fire"), Door(tx, ty, "water")]
       fb_pos = (start_x * TILE, start_y * TILE)
       wg_pos = (start_x * TILE, start_y * TILE)
       return tiles, pools, moving_platforms, gems, doors, fb_pos, wg_pos
   ```

2. Register it in the three lists near the bottom of the file:
   ```python
   LEVEL_BUILDERS.append(build_level_4)
   LEVEL_NAMES.append("Level 4 – Your Name Here")
   LEVEL_THEMES.append((25, 10, 30))   # Any (R, G, B)
   ```

That's all. The rest of the game (transitions, scoring, win detection) works automatically.

### Change the physics

All physics values are constants at the top of the file:
```python
GRAVITY    = 0.55    # Higher = heavier feel
JUMP_POWER = -13.5   # More negative = higher jump
MOVE_SPEED = 4.5     # Higher = faster characters
MUD_SLOW   = 0.4     # Lower = more dramatic mud slowdown
MAX_FALL   = 18      # Higher = faster terminal velocity
```

### Change character colors

Edit the `C_FIRE_*` and `C_WATER_*` constants at the top. Colors propagate everywhere automatically.

### Change platform speed in a level

In any `MovingPlatform(...)` call, increase `speed`:
- `speed=0.8` → leisurely (Level 1 feel)
- `speed=1.5` → challenging (Level 2 feel)  
- `speed=2.0` → frantic (Level 3 feel)

Use `phase=0.5` on a second platform to make it move in the opposite direction from the first.

---

*End of reference guide.*
