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
from adafruit_display_text import label
from fourwire import FourWire
import time

from adafruit_st7735r import ST7735R


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

def SprigScreen():
    # Release any resources currently in use for the displays
    displayio.release_displays()

    spi = busio.SPI(board.GP18, board.GP19)

    if spi.try_lock():
        spi.configure(baudrate=64000000)
        spi.unlock()

    tft_cs = board.GP20
    tft_dc = board.GP22

    display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.GP26)

    return ST7735R(display_bus, width=160, height=128, rotation=270, bgr=True)

class SprogDisplay:
    def __init__(self, screen):
        screen.auto_refresh = False
        palette = create_cheerful24_palette()
        self.bitmap = displayio.Bitmap(160, 128, 24)  # can use all 24 colors
        self.sprite = displayio.TileGrid(self.bitmap, pixel_shader=palette)

        splash = displayio.Group()
        splash.append(self.sprite)
        screen.root_group = splash
        self.screen = screen

    def cls(self, color=0):
        """clear screen"""
        self.bitmap.fill(color & 15)

    def pset(self, x, y, color):
        """set pixel"""
        if 0 <= x < 160 and 0 <= y < 128:
            self.bitmap[x, y] = color & 15



class Sprog:
    def __init__(self):
        self.display = SprogDisplay(SprigScreen())

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

    def addText(self, x, y, text):
        """Called when adding text"""
        label = label.Label(terminalio.FONT, text=text, color=[15, 15, 18])

        label.x = x
        label.y = y
        self.splash.append(label)
    def clearText(self):
        """Called when deleting text"""
        label.Label.remove(layer=self.splash)
    def run(self):
        """Start the game loop"""
        self.init()
        frame_time = 1.0 / 30



        while self.running:
            frame_start = time.monotonic()

            # call user methods
            self.update()
            self.draw()
            self.clearText()
            self.display.screen.refresh()

            self.frame_count += 1

            # maintain framerate
            elapsed = time.monotonic() - frame_start
            if elapsed < frame_time:
                time.sleep(frame_time - elapsed)
