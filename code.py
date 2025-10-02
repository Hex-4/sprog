import sprog
import gc

gc.collect()
print(str(gc.mem_free())+"        ")

playerSprite = [
    ".....",
    ".....",
    "hh33h",
    "hh33h",
]

class TestGame(sprog.Sprog):
    def init(self):
        self.x, self.y = 0, 0
    def update(self):
        i = self.input
        d = self.display
        dx, dy = i.dir()
        self.x += dx
        self.y += dy

        dx, dy = i.dir("right")
        self.x += dx * 3
        self.y += dy * 3


        if i.btn("i") == True:
            d.clearText()
            d.addText(x=1, y=5, text=f"frame: {self.frame_count}")
            d.addText(x=1, y=15, text=f"fps: {self.elapsed * 30}")
            d.addText(x=1, y=25, text=f"x: {dx}")
            d.addText(x=1, y=35, text=f"y: {dy}")
            gc.collect()
        else:
            d.clearText()

    def draw(self):
        d = self.display
        d.cls(6)
        d.renderBitmap(self.x, self.y, playerSprite)

game = TestGame()
game.run()
 # type: ignore
