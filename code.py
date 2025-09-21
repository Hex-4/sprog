import sprog

playerSprite = [
    "......",
    "......",
    "......",
    "......",
    "......",
    "......",
]

class TestGame(sprog.Sprog):
    def init(self):
        self.x, self.y = 0, 0
        self.addText(x=1, y=1, text="hello world!")
    def update(self):
        i = self.input
        
        dx, dy = i.dir()
        self.x += dx
        self.y += dy
        
        dx, dy = i.dir("right")
        self.x += dx * 3
        self.y += dy * 3
        
    def draw(self):
        d = self.display

        d.cls(2)
        d.cls(3)
        d.cls(4)
        d.cls(5)
        d.cls(6)
        d.pset(self.x, self.y, 14)

game = TestGame()
game.run()
 # type: ignore