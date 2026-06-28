# Silverspark

*An AFK barding-salvage bot for Conqueror's Blade.*

Automates buying **Shielded Chanfron** items from the Barding & Tack vendor and
salvaging them in bulk. It drives the game with `pydirectinput` at fixed
**1920×1080** screen coordinates, using deterministic *move → settle → click*
timing (plus a small re-assert + jiggle) so clicks register reliably in the
DirectX client. Toggled on/off with a global **F12** hotkey.

## Before running

- Run the game at **1920×1080 borderless/fullscreen** on your **primary** monitor.
- Run the terminal **as Administrator** — both the global F12 hotkey and the
  DirectInput injection into the game need it.
- Turn **off** Windows **"Enhance pointer precision"**
  (*Settings → Bluetooth & devices → Mouse → Additional mouse settings →
  Pointer Options*). Mouse acceleration distorts injected movement and is a real
  cause of missed clicks.

## Install

```
pip install -r requirements.txt
```

## Run

```
python silverspark.py
```

- **F12** — start the bot (5-second countdown) / stop it **immediately** (works
  even during the 22-second salvage wait).
- **Mouse to a screen corner** — hard abort (pyautogui failsafe).
- **Ctrl+C** in the terminal — exit.

## What it does each cycle

1. `F` → open the vendor dialog → click **Barding & Tack** to open the shop.
2. Buy **Shielded Chanfron** ×3 — click Buy, type `100` (the game caps the field
   at 20 → 60 items total), click Buy in the dialog (which closes it; **no Esc**
   between purchases). After 3 buys, `Esc` once to close the shop.
3. `I` → open inventory → click the **Salvage** icon (two circular arrows).
4. For **6 batches**: right-click each of the next **10 items twice**, click
   **Salvage**, click **Yes**, wait 22 s, `Esc`.
5. `Esc` `Esc`, then start over.

The 60 items fill fixed inventory slots; each batch targets the next 10 slots,
generated from `GRID_ORIGIN` / `GRID_CELL` / `GRID_COLUMNS`.

## Calibrating coordinates (only if clicks land wrong)

The coordinates in `silverspark.py` are **already measured** from the reference
screenshots for 1920×1080 and ship working. You only need to recalibrate if your
UI differs (resolution, HUD scale, ultrawide, etc.).

```
python silverspark.py --calibrate
```

This prints the live mouse position. Hover each element and copy the printed
`x y` into the `CONFIG` block of `silverspark.py`:

| Constant         | Hover over…                                            |
|------------------|--------------------------------------------------------|
| `BARDING_TACK`   | the "Barding & Tack" dialog option (step_2)            |
| `BUY_CHANFRON`   | the "Buy" button on Shielded Chanfron (step_3)         |
| `QTY_FIELD`      | the quantity input field (step_4)                      |
| `BUY_CONFIRM`    | the "Buy" button in the purchase dialog (step_4)       |
| `SALVAGE_ICON`   | the salvage icon — two circular arrows (step_5)        |
| `SALVAGE_BUTTON` | the "Salvage" button (step_6/7)                        |
| `CONFIRM_YES`    | the "Yes" confirm button (step_8)                      |
| `GRID_ORIGIN`    | center of the **first** inventory slot (step_6)        |
| `GRID_CELL`      | hover slot 1 and slot 2 — the difference is the pitch  |
| `GRID_COLUMNS`   | number of slots per inventory row (currently 8)        |

The 60 item slots are generated from `GRID_ORIGIN`, `GRID_CELL`, and
`GRID_COLUMNS`, so you only tune a few numbers, not 60 coordinates.

## Tuning

All knobs live in the `CONFIG` block at the top of `silverspark.py`.

**If a click doesn't register** (cursor is on the box but nothing happens):
- Make sure "Enhance pointer precision" is off (see *Before running*).
- Increase `JIGGLE` (e.g. `4` → `8`) for a bigger hover-triggering nudge.
- Increase the relevant settle: `BARDING_SETTLE`, `BUY_SETTLE`, `SALVAGE_SETTLE`
  (the move→press delay for that click), or `MOVE_SETTLE` for all clicks.

**If actions fire before the UI is ready**, increase the matching pause:
- `MENU_PAUSE` — generic menu open/close.
- `SHOP_OPEN_PAUSE` — after the shop opens, before the first Buy click.
- `PRE_SALVAGE_PAUSE` — after the last item is added, before pressing Salvage.
- `SALVAGE_WAIT` — the wait after confirming a salvage.
