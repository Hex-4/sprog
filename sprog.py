


from displayio import Palette


import board
import displayio
from microcontroller import Pin
import terminalio
import busio
import digitalio
import math
from adafruit_display_text import bitmap_label
from fourwire import FourWire
import time
import gc

from adafruit_st7735r import ST7735R

def normalize(vector: list[int]) -> list[float] | list[int]:
    """
    Turns a vector into a unit vector.


    :param list vector: The vector (in the form of [0,0]) to normalize.
    
    :return: The normalized vector (in the form of [0,0])
    """
    if vector[0] + vector[1] > 0:
        magnitude = math.sqrt(sum(x**2 for x in vector))
        return [x / magnitude for x in vector]
    else:
        return vector



def create_cheerful24_palette() -> Palette:
    """
    (for internal use) Creates the Sprog palette for use with displayio.
    
    :return: a displayio Palette object.
    """
    palette: Palette = displayio.Palette(color_count=24)

    # Cheerful-24 colors (RGB values)
    colors: list[tuple[int, int, int]] = [
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

def SprigScreen() -> ST7735R:
    """
    (for internal use) A display adapter for the ST7735R (the default Sprig display), initialized at the start
    
    :return: A ST7735R object (BusDisolay)
    """
    # Release any resources currently in use for the displays
    displayio.release_displays()

    spi = busio.SPI(board.GP18, board.GP19) # pyright: ignore[reportAttributeAccessIssue]

    if spi.try_lock():
        spi.configure(baudrate=64000000) # Speed up screen drawing
        spi.unlock()
        spi.unlock()

    tft_cs = board.GP20 # pyright: ignore[reportAttributeAccessIssue]
    tft_dc = board.GP22 # pyright: ignore[reportAttributeAccessIssue]

    display_bus = FourWire(spi, command=tft_dc, chip_select=tft_cs, reset=board.GP26) # pyright: ignore[reportAttributeAccessIssue]

    return ST7735R(display_bus, width=160, height=128, rotation=270, bgr=True)

class SprogDisplay:
    """
    (automatically initalized) The Sprog display API. Includes methods for displaying pixels, text, and bitmaps.
    
    :param BusDisplay screen: A BusDisplay object to connect to. Use a display adapter like SprigScreen() to get this.
    """
    def __init__(self, screen) -> None:
        screen.auto_refresh = False # We refresh in draw()
        self.palette = create_cheerful24_palette()
        self.bitmap = displayio.Bitmap(160, 128, 24)  # can use all 24 colors
        self.sprite = displayio.TileGrid(self.bitmap, pixel_shader=self.palette)

        self.splash = displayio.Group()
        self.splash.append(self.sprite)
        screen.root_group = self.splash
        self.screen = screen
        self.texts = []
        
        # Creates the Sprog palette for use with sprites.
        self.colorSymbols = [
            "0",  # dark black
            "1",  # dark gray
            "2",  # light gray
            "3",  # white
            "a",  # cyan
            "b",  # blue
            "c",  # dark blue
            "d",  # navy
            "e",  # dark teal
            "f",  # green
            "g",  # bright green 11
            "h",  # light green
            "i",  # light yellow
            "j",  # yellow
            "k",  # orange
            "l",  # red
            "m",  # dark red
            "n",  # maroon
            "o",  # brown
            "p",  # light brown
            "q",  # tan
            "r",  # peach
            "s",  # pink
            "t",  # purple
        ]


    def renderBitmap(self, x: float, y: float, bitmap: list[str]) -> None:
        """
        Render a bitmap array to the screen, with the top left corner at x, y (this is an advanced function, for most uses the Sprite API is better)
        :param float x: X position, in pixels, of the top left corner
        :param float y: Y position, in pixels, of the top left corner
        :param list[str] bitmap: A bitmap array using the palette colorSymbols
        """
        for (rowIndex, row) in enumerate(bitmap):
            for (pixelIndex, pixel) in enumerate(bitmap[rowIndex]):
                if pixel != ".":
                    self.pset(pixelIndex + x, rowIndex + y, self.colorSymbols.index(pixel))

    def cls(self, color: int = 0) -> None:
        """
        Clear screen
        :param int color: The color index that the screen should be set to.
        """
        self.bitmap.fill(color & 15)

    def pset(self, x: float, y: float, color: int) -> None:
        """
        Sets a pixel to a color on the screen.
        :param float x: The X position of the pixel
        :param float y: The Y position of the pixel
        :param int color: The color index to set the pixel to
        """
        if 0 <= x < 160 and 0 <= y < 128: # if pixel in bounds
            self.bitmap[math.floor(x), math.floor(y)] = color & 15 # set in bitmap

    def addText(self, x: int, y: int, text: str, color: int = 3, centered: bool = False) -> bitmap_label:
        """
        Create text to be displayed on the screen. Persists across cls() calls until removed with clearText().
        :param int x: The X position of the text
        :param int y: The Y position of the text
        :param str text: The text to render
        :param int color: The color index to use for the text
        :param bool centered: Whether to center the text or anchor at the top left corner
        """
        l = bitmap_label.Label(terminalio.FONT, text=text, color=self.palette[color])
        if centered:
            l.anchor_point = (0.5, 0.5)
        else:
            l.anchor_point = (0, 0)
        l.anchored_position = (x, y)
        self.splash.append(l)
        self.texts.append(l)


        return l
    def clearText(self) -> None:
        """
        Deletes all text labels.
        """
        for i in self.texts:
            if i in self.splash:
                self.splash.remove(i)

                del i
                print(str(gc.mem_free())+"        ")

        gc.collect()
        self.texts.clear()


class SprogInput:
    """
    The Sprog input API. Includes polling, state checking, press detection, and many other helpers.
    
    (automatically initialized on boot)
    """
    def __init__(self) -> None:
        """
        Initalizes the input API by creating DigitalInOuts for all buttons.
        """
        pins: dict[str, Pin] = {
            "w": board.GP5, # pyright: ignore[reportAttributeAccessIssue]
            "a": board.GP6, # pyright: ignore[reportAttributeAccessIssue]
            "s": board.GP7, # pyright: ignore[reportAttributeAccessIssue]
            "d": board.GP8, # pyright: ignore[reportAttributeAccessIssue]

            "i": board.GP12, # pyright: ignore[reportAttributeAccessIssue]
            "j": board.GP13, # pyright: ignore[reportAttributeAccessIssue]
            "k": board.GP14, # pyright: ignore[reportAttributeAccessIssue]
            "l": board.GP15  # pyright: ignore[reportAttributeAccessIssue]
        }

        self.buttons: dict[str, int] = {
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
        """
        Polls all buttons, runs every frame automatically.
        """
        for name, io in self.ios.items():
            if not io.value: # if pressed
                self.buttons[name] += 1
            else:
                self.buttons[name] = 0
    
    def btn(self, name: str) -> bool:
        """
        Check if the button is pressed or held at all
        
        :param str name: The letter name of the button to check
        """
        if self.buttons[name] > 0:
            return True
        else:
            return False
        
    def btnp(self, name) -> bool:
        """
        Check if the button was just pressed (True for one frame only)
        
        :param str name: The letter name of the button to check
        """
        if self.buttons[name] == 1:
            return True
        else:
            return False
    
    def btna(self) -> list[str]:
        """Get a list of the buttons currently pressed"""
        pressed: list[str] = []
        for btn, frames in self.buttons.items():
            if frames > 0:
                pressed.append(btn)
        return pressed
    
    
    def btnf(self, name) -> int:
        """Get how many frames a button was pressed for"""
        return self.buttons[name]
    
    def dir(self, side = "left") -> list[float] | list[int]:
        """
        Get a vector (list with two numbers, like [-1, 1]) representing the current state of either side of buttons. Add these values to your player's x and y coordinates to quickly make a movement system. Automatically normalizes the result so diagonal movement isn't faster.
        
        For example, if the up button is pressed, this returns [0, 1].
        
        :param str side: Which side ("left" or "right") to poll.
        """
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
    """
    A Sprog game. Extend this class to make your own! This includes a menu, initalizes all subclasses, and has draw() and update() functions for you to overwrite.
    """
    def __init__(self):
        """
        Initializes a Sprog game.
        """

        self.display = SprogDisplay(SprigScreen())
        self.input = SprogInput()

        
        self.frame_count = 0

        # self.running = True for automaticly going to the game. Perfect for testing games.
        self.running = False

        self.init_metadata()

        gc.enable()

    def init_metadata(self) -> None:
        """
        Set up your game's metadata here!
        """
        self.gameTitle = "Untitled Game"

    def init(self):
        """Called once at startup - override this!"""
        pass

    def update(self):
        """Called every frame before draw - override this!"""
        pass

    def draw(self):
        """Called every frame after update - override this!"""
        pass

    def run(self):
        """Starts the game loop"""
        self.init()
        frame_time = 1.0 / 30
        while self.running == False:
            self.display.cls(3)
            self.display.pset(x=160, y=42, color=10)
            self.display.addText(x=80, y=21, text=self.gameTitle, color=3, centered=True)
            self.display.addText(x=80, y=64, text="Press J to start!", color=0, centered=True)
            self.display.screen.refresh()
            self.input.poll()

            if self.input.btn("j") == True:
                self.running = True
        while self.running:
            frame_start = time.monotonic()

            # call user methods
            self.input.poll()
            self.update()
            self.draw()
            self.display.screen.refresh()

            self.frame_count += 1

            # maintain framerate
            self.elapsed = time.monotonic() - frame_start
            if self.elapsed < frame_time:
                time.sleep(frame_time - self.elapsed)
