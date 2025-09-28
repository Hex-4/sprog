# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
This test will initialize the display using displayio and draw a solid green
background, a smaller purple rectangle, and some yellow text.
"""


import board
import displayio
import terminalio
import busio
import digitalio
import math
from adafruit_display_text import label
from fourwire import FourWire
import time

from adafruit_st7735r import ST7735R

def normalize(vector):
    if vector[0] + vector[1] > 0:
        magnitude = math.sqrt(sum(x**2 for x in vector))
        return [x / magnitude for x in vector]
    else:
        return vector



def create_cheerful24_palette():
    palette = displayio.Palette(24)

    # Cheerful-24 colors (RGB values)
    colors = [
        (15, 15, 18),      # 0 - dark black
        (80, 83, 89),      # 1 - dark gray
        (182, 191, 188),   # 2 - light gray
        (242, 251, 255),   # 3 - white
        (94, 231, 255),    # 4 - cyan
        (0, 161, 219),     # 5 - blue
        (29, 91, 184),     # 6 - dark blue
        (31, 44, 102),     # 7 - navy
        (27, 82, 69),      # 8 - dark teal
        (46, 143, 70),     # 9 - green
        (88, 217, 46),     # 10 - bright green
        (203, 255, 112),   # 11 - light green
        (255, 255, 143),   # 12 - light yellow
        (255, 223, 43),    # 13 - yellow
        (240, 119, 26),    # 14 - orange
        (227, 34, 57),     # 15 - red
        (133, 21, 64),     # 16 - dark red
        (64, 26, 36),      # 17 - maroon
        (156, 59, 48),     # 18 - brown
        (201, 93, 60),     # 19 - light brown
        (237, 138, 95),    # 20 - tan
        (255, 188, 166),   # 21 - peach
        (235, 117, 190),   # 22 - pink
        (119, 56, 140),    # 23 - purple
    ]

    # convert RGB to 24-bit color values
    for i, (r, g, b) in enumerate(colors):
        palette[i] = (r << 16) | (g << 8) | b

    return palette

class Sprite:
    def __init__(self, img: list[str]) -> None:
        self.img = img

def SprigScreen():
    # Release any resources currently in use for the displays
    displayio.release_displays()

    spi = busio.SPI(board.GP18, board.GP19) # pyright: ignore[reportAttributeAccessIssue]

    if spi.try_lock():
        spi.configure(baudrate=64000000)
        spi.unlock()

    tft_cs = board.GP20 # pyright: ignore[reportAttributeAccessIssue]
    tft_dc = board.GP22 # pyright: ignore[reportAttributeAccessIssue]

    display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.GP26) # pyright: ignore[reportAttributeAccessIssue]

    return ST7735R(display_bus, width=160, height=128, rotation=270, bgr=True)

class SprogDisplay:
    def __init__(self, screen):
        screen.auto_refresh = False
        palette = create_cheerful24_palette()
        self.bitmap = displayio.Bitmap(160, 128, 24)  # can use all 24 colors
        self.sprite = displayio.TileGrid(self.bitmap, pixel_shader=palette)

        self.splash = displayio.Group()
        self.splash.append(self.sprite)
        screen.root_group = self.splash
        self.screen = screen

    def cls(self, color=0):
        """clear screen"""
        self.bitmap.fill(color & 15)

    def pset(self, x, y, color):
        """set pixel"""
        if 0 <= x < 160 and 0 <= y < 128:
            self.bitmap[math.floor(x), math.floor(y)] = color & 15

    def addText(self, x, y, text):
        """Called when adding text"""
        l = label.Label(terminalio.FONT, text=text)
        l.x = x
        l.y = y
        self.splash.append(l)
        return l
    def clearText(self, label):
        """Called when deleting text"""
        self.splash.remove(label)

class SprogInput:
    def __init__(self) -> None:
        pins = {
            "w": board.GP5, # pyright: ignore[reportAttributeAccessIssue]
            "a": board.GP6, # pyright: ignore[reportAttributeAccessIssue]
            "s": board.GP7, # pyright: ignore[reportAttributeAccessIssue]
            "d": board.GP8, # pyright: ignore[reportAttributeAccessIssue]

            "i": board.GP12, # pyright: ignore[reportAttributeAccessIssue]
            "j": board.GP13, # pyright: ignore[reportAttributeAccessIssue]
            "k": board.GP14, # pyright: ignore[reportAttributeAccessIssue]
            "l": board.GP15  # pyright: ignore[reportAttributeAccessIssue]
        }

        self.buttons = {
            "w": 0,
            "a": 0,
            "s": 0,
            "d": 0,

            "i": 0,
            "j": 0,
            "k": 0,
            "l": 0,
        }

        self.ios: dict[str, digitalio.DigitalInOut] = {}

        for name, pin in pins.items():
            btn = digitalio.DigitalInOut(pin)
            btn.direction = digitalio.Direction.INPUT
            btn.pull = digitalio.Pull.UP
            self.ios[name] = btn

    def poll(self) -> None:
        for name, io in self.ios.items():
            if not io.value: # if pressed
                self.buttons[name] += 1
            else:
                self.buttons[name] = 0
    """If the button is is pressed or hold"""
    def btn(self, name: str) -> bool:
        if self.buttons[name] > 0:
            return True
        else:
            return False
    """If the button is is pressed for one frame (aka no hold)"""
    def btnp(self, name):
        if self.buttons[name] == 1:
            return True
        else:
            return False
    """Sendes a list of the buttons cuerrently pressed"""
    def btna(self):
        pressed: list[str] = []
        for btn, frames in self.buttons.items():
            if frames > 0:
                pressed.append(btn)
        return pressed
    """How long is the button holded"""
    def btnf(self, name):
        return self.buttons[name]

    def dir(self, side = "left"):
        values: dict[str, list[int]] = {}
        if side == "left":
            values = {
                "w": [0, -1],
                "a": [-1, 0],
                "s": [0, 1],
                "d": [1, 0],
            }
        elif side == "right":
            values = {
                "i": [0, -1],
                "j": [-1, 0],
                "k": [0, 1],
                "l": [1, 0],
            }
        vector = [0, 0]
        for btn in self.btna():
            if btn in values:
                vector[0] += values[btn][0]
                vector[1] += values[btn][1]

        return normalize(vector)


class Sprog:
    def __init__(self):
        self.display = SprogDisplay(SprigScreen())
        self.input = SprogInput()

        self.running = True

        self.frame_count = 0



    def init(self):
        """Called once at startup - override this"""
        pass

    def update(self):
        """Called every frame before draw - override this"""
        pass

    def draw(self):
        """Called every frame after update - override this"""
        pass

    def run(self):
        """Start the game loop"""
        self.init()
        frame_time = 1.0 / 30



        while self.running:
            frame_start = time.monotonic()

            # call user methods
            self.input.poll()
            self.update()
            self.draw()
            self.display.screen.refresh()

            self.frame_count += 1

            # maintain framerate
            elapsed = time.monotonic() - frame_start
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
