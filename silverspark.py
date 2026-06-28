"""
Silverspark
===========
Conqueror's Blade salvage bot.

Automates buying "Shielded Chanfron" items from the Barding & Tack vendor and
salvaging them in bulk. Driven entirely by simulated mouse clicks at fixed
1920x1080 screen coordinates and keyboard input.

Controls
--------
  F12  : toggle the bot on/off. On start there is a 5 second delay; pressing F12
         again stops the bot IMMEDIATELY (even during the 22s salvage wait).
  Move the mouse to a screen corner at any time to hard-abort (pyautogui failsafe).
  Ctrl+C in the terminal also exits.

Calibration
-----------
  python silverspark.py --calibrate
  Prints the live mouse position so you can hover each UI element in-game and copy
  exact coordinates into the CONFIG block below.

Notes
-----
  * Conqueror's Blade is a DirectX game, so we use pydirectinput (scancode/DirectInput
    events) for all in-game input. Run the terminal AS ADMINISTRATOR so both the F12
    hotkey and the injected input work reliably.
  * Assumes the game runs at 1920x1080 borderless/fullscreen on the primary monitor.
"""

import sys
import time
import threading

import pyautogui
import pydirectinput
import keyboard

# ===========================================================================
# CONFIG  --  tune these to your setup (see --calibrate)
# ===========================================================================

# Timing (seconds) -- all fixed, no randomness
START_DELAY     = 5.0    # delay after pressing F12 before the bot acts
ACTION_PAUSE    = 0.4    # pause after each individual click / keypress
MENU_PAUSE      = 1.0    # pause after opening or closing a menu
TYPE_INTERVAL   = 0.05   # delay between typed characters
KEY_HOLD        = 0.08   # time to HOLD each key down (DirectX games miss instant taps)
CLICK_HOLD      = 0.12   # how long to hold each mouse button down
JIGGLE          = 4      # px nudge at the target to make the game register the hover
QTY_CLICK_HOLD  = 0.30   # longer hold for the quantity field so it takes focus
DOUBLE_RCLICK_GAP = 0.35 # gap between the 1st and 2nd RMB press on each item
MOVE_SETTLE     = 0.5    # fixed delay between the cursor arriving and the button press
SALVAGE_SETTLE  = 0.8    # larger move->press delay for the Salvage button specifically
PRE_SALVAGE_PAUSE = 1.0  # pause after the last item is added, before pressing Salvage
SHOP_OPEN_PAUSE = 1.8    # wait for the shop to finish opening before the first Buy click
BUY_SETTLE      = 0.8    # larger move->press delay for the Buy-Chanfron click
BARDING_SETTLE  = 0.8    # move->press delay for the "Barding & Tack" click (open shop)
MOVE_DURATION   = 0.25   # travel time for the cursor to move from A to B
KEY_GAP         = 1.0    # extra delay between two key presses in a row (e.g. Esc, Esc)
SALVAGE_WAIT    = 22.0   # wait after confirming a salvage (interruptible)
RESTART_ESC_GAP = 0.4    # delay between the two restart Esc presses

# Workflow counts
BUY_REPEATS     = 3      # buy Shielded Chanfron this many times (3 x 20 = 60 items)
SALVAGE_BATCHES = 6      # number of salvage rounds
ITEMS_PER_BATCH = 10     # items selected per salvage round
BUY_QUANTITY    = "100"  # typed into qty field; the game caps it at 20

# --- Screen coordinates (x, y) at 1920x1080 ------------------------------
# Measured directly from the reference screenshots in pictures/ (full-resolution
# crops). If your UI differs, re-check with --calibrate.
BARDING_TACK   = (1560, 915)   # step_2  : "Barding & Tack" dialog option
BUY_CHANFRON   = (470, 297)    # step_3  : "Buy" button on Shielded Chanfron (top item)
QTY_FIELD      = (1000, 578)   # step_4  : quantity input field (just right of the "1")
BUY_CONFIRM    = (808, 674)    # step_4  : "Buy" button in the purchase dialog
SALVAGE_ICON   = (1253, 490)   # step_5  : salvage icon (two arrows forming a circle)
SALVAGE_BUTTON = (285, 880)    # step_6/7: "Salvage" button
CONFIRM_YES    = (808, 640)    # step_8  : "Yes" confirm button

# Inventory grid for the 60 bought items (step_6). Slot coordinates are GENERATED
# from these three values, so calibration is just a couple of numbers.
GRID_ORIGIN    = (1330, 220)   # center of the first (top-left) inventory slot
GRID_CELL      = (77, 77)      # (x pitch, y pitch) between adjacent slots
GRID_COLUMNS   = 8             # slots per inventory row (top row holds 8 items)

# ===========================================================================
# Internals
# ===========================================================================

# pyautogui corner failsafe stays on; we use its position() for calibration.
pyautogui.FAILSAFE = True
pydirectinput.PAUSE = 0.0  # we manage our own pauses

running = threading.Event()   # set = bot active, clear = bot idle
_last_was_key = False         # True if the previous action was a key press


class Stopped(Exception):
    """Raised to unwind the workflow immediately when the bot is stopped."""


def _check():
    """Abort the current workflow the instant the bot is toggled off."""
    if not running.is_set():
        raise Stopped


def interruptible_sleep(seconds):
    """Sleep that wakes up immediately if the bot is stopped."""
    end = time.time() + seconds
    while time.time() < end:
        _check()
        time.sleep(0.05)


def start_countdown():
    """Print a 1-second-tick countdown before the bot acts. F12 cancels it."""
    whole = int(START_DELAY)
    print(f"[COUNTDOWN] bot starting in {whole} seconds... (F12 to cancel)")
    for s in range(whole, 0, -1):
        _check()
        print(f"  starting in {s}...")
        interruptible_sleep(1.0)
    frac = START_DELAY - whole
    if frac > 0:
        interruptible_sleep(frac)
    print("[COUNTDOWN] go!")


def tap(key):
    """Press a key, holding it briefly so DirectX games actually register it.
    If the previous action was also a key press, wait KEY_GAP first."""
    global _last_was_key
    _check()
    if _last_was_key:
        interruptible_sleep(KEY_GAP)
    pydirectinput.keyDown(key)
    time.sleep(KEY_HOLD)
    pydirectinput.keyUp(key)
    _last_was_key = True
    interruptible_sleep(ACTION_PAUSE)


def _do_click(point, button, hold=None, settle=None):
    global _last_was_key
    _last_was_key = False
    x, y = point
    # Travel to the target (interpolated)...
    pydirectinput.moveTo(x, y, duration=MOVE_DURATION)
    # ...then re-assert the exact position and jiggle off-and-back, so the game
    # gets a fresh movement event and registers the cursor's hover before we press.
    pydirectinput.moveTo(x, y)
    pydirectinput.moveTo(x + JIGGLE, y)
    pydirectinput.moveTo(x, y)
    time.sleep(MOVE_SETTLE if settle is None else settle)
    pydirectinput.mouseDown(button=button)
    time.sleep(CLICK_HOLD if hold is None else hold)
    pydirectinput.mouseUp(button=button)
    interruptible_sleep(ACTION_PAUSE)


def click(point, hold=None, settle=None):
    _check()
    _do_click(point, "left", hold, settle)


def rclick(point):
    _check()
    _do_click(point, "right")


def rclick_twice(point):
    """Move to an item, then press RMB twice on the same spot. The 2nd press
    happens DOUBLE_RCLICK_GAP after the 1st (the cursor is not moved between them)."""
    global _last_was_key
    _check()
    _last_was_key = False
    x, y = point
    pydirectinput.moveTo(x, y, duration=MOVE_DURATION)
    # Re-assert + jiggle so the game registers the hover on this item (see _do_click).
    pydirectinput.moveTo(x, y)
    pydirectinput.moveTo(x + JIGGLE, y)
    pydirectinput.moveTo(x, y)
    time.sleep(MOVE_SETTLE)
    for n in range(2):
        if n == 1:
            time.sleep(DOUBLE_RCLICK_GAP)   # wait before the 2nd RMB
        pydirectinput.mouseDown(button="right")
        time.sleep(CLICK_HOLD)
        pydirectinput.mouseUp(button="right")
    interruptible_sleep(ACTION_PAUSE)


def type_text(text):
    global _last_was_key
    _check()
    for ch in text:
        _check()
        pydirectinput.keyDown(ch)
        time.sleep(KEY_HOLD)
        pydirectinput.keyUp(ch)
        time.sleep(TYPE_INTERVAL)
    _last_was_key = True
    interruptible_sleep(ACTION_PAUSE)


def slot_xy(index):
    """Map a global item index (0..59) to a screen coordinate."""
    row, col = divmod(index, GRID_COLUMNS)
    ox, oy = GRID_ORIGIN
    cx, cy = GRID_CELL
    return (ox + col * cx, oy + row * cy)


# ===========================================================================
# Workflow phases
# ===========================================================================

def buy_phase():
    # Step 1: open the vendor dialog.
    tap("f")
    interruptible_sleep(MENU_PAUSE)

    # Step 2: choose "Barding & Tack" -> opens the shop. Wait for the open
    # animation to finish so the first Buy button is interactive.
    click(BARDING_TACK, settle=BARDING_SETTLE)
    interruptible_sleep(SHOP_OPEN_PAUSE)

    # Steps 3-4 (x BUY_REPEATS): buy Shielded Chanfron.
    # Clicking "Buy" in the dialog confirms the purchase AND closes the dialog,
    # returning to the shop list -- so we do NOT press Esc between purchases
    # (that would close the whole shop). We just open the dialog and buy again.
    for n in range(BUY_REPEATS):
        print(f"  buying Shielded Chanfron ({n + 1}/{BUY_REPEATS})")
        click(BUY_CHANFRON, settle=BUY_SETTLE)  # open purchase dialog
        interruptible_sleep(MENU_PAUSE)
        click(QTY_FIELD, hold=QTY_CLICK_HOLD)  # longer hold so the field takes focus
        type_text(BUY_QUANTITY)  # game caps this at 20
        click(BUY_CONFIRM)       # confirm purchase -> dialog closes, back to shop
        interruptible_sleep(MENU_PAUSE)        # let the dialog close before next buy

    # Close the barding shop before opening the inventory.
    tap("esc")
    interruptible_sleep(MENU_PAUSE)


def salvage_phase():
    # Step 5: open inventory and the Salvaging window.
    tap("i")
    interruptible_sleep(MENU_PAUSE)
    click(SALVAGE_ICON)
    interruptible_sleep(MENU_PAUSE)

    # Steps 6-9 (x SALVAGE_BATCHES).
    for b in range(SALVAGE_BATCHES):
        print(f"  salvage batch {b + 1}/{SALVAGE_BATCHES}")
        # Step 6: right-click the next 10 items (twice each).
        for i in range(ITEMS_PER_BATCH):
            rclick_twice(slot_xy(b * ITEMS_PER_BATCH + i))
        # Step 7: press Salvage. Pause first so the panel finishes registering the
        # last item and the button becomes active after the right-click burst.
        interruptible_sleep(PRE_SALVAGE_PAUSE)
        click(SALVAGE_BUTTON, settle=SALVAGE_SETTLE)
        interruptible_sleep(MENU_PAUSE)   # wait for the confirm popup to appear
        # Step 8: confirm.
        click(CONFIRM_YES)
        # Step 9: wait, then Esc.
        interruptible_sleep(SALVAGE_WAIT)
        tap("esc")
        interruptible_sleep(ACTION_PAUSE)


def restart():
    # Step 11: two Esc presses with a slight delay, then loop.
    tap("esc")
    interruptible_sleep(RESTART_ESC_GAP)
    tap("esc")
    interruptible_sleep(MENU_PAUSE)


def run_cycle():
    buy_phase()       # steps 1-4.5
    salvage_phase()   # steps 5-10
    restart()         # step 11


# ===========================================================================
# Hotkey + main loop
# ===========================================================================

def toggle():
    if running.is_set():
        running.clear()
        print("\n[STOP] bot stopped.")
    else:
        running.set()
        print(f"\n[START] bot starting in {START_DELAY:.0f}s... (F12 to stop)")


def calibrate():
    print("Calibration mode. Hover a UI element to read its (x, y). Ctrl+C to quit.")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"  x={x:<5} y={y:<5}", end="\r")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nDone.")


def main():
    if "--calibrate" in sys.argv:
        calibrate()
        return

    keyboard.add_hotkey("f12", toggle)
    print("Salvage bot ready. Press F12 to start/stop. Ctrl+C to exit.")
    print("(Move mouse to a screen corner to hard-abort.)")

    try:
        while True:
            # Idle until F12 turns the bot on.
            running.wait()
            try:
                start_countdown()
                print("[RUN] working...")
                while running.is_set():
                    run_cycle()
            except Stopped:
                # Toggled off mid-workflow; fall back to idle.
                pass
            except pyautogui.FailSafeException:
                running.clear()
                print("\n[ABORT] failsafe triggered (mouse in corner). Bot stopped.")
    except KeyboardInterrupt:
        print("\nExiting.")


if __name__ == "__main__":
    main()
