import sprog
import math
import microcontroller

microcontroller.cpu.frequency = 300_000_000

class FastPlasmaDemo(sprog.Sprog):
    def init(self):
        self.time = 0
        
        # pre-calculate lookup tables for speed
        self.sin_table = []
        for i in range(256):
            self.sin_table.append(math.sin(i * 2 * math.pi / 256))
        
        # bigger pixels for speed
        self.pixel_size = 4
        self.width = 160 // self.pixel_size
        self.height = 128 // self.pixel_size
        
        # color cycling
        self.color_offset = 0
    
    def fast_sin(self, val):
        """Fast sine using lookup table"""
        idx = int(val * 40) & 255  # wrap around
        return self.sin_table[idx]
    
    def update(self):
        self.time += 0.1
        self.color_offset = (self.color_offset + 1) % 24
    
    def draw(self):
        d = self.display
        d.cls(0)
        
        # much bigger pixels, way fewer calculations
        for y in range(self.height):
            for x in range(self.width):
                # simpler plasma calculation
                val = (self.fast_sin(x * 0.5 + self.time) + 
                       self.fast_sin(y * 0.4 + self.time * 1.2)) * 0.5
                
                # map to color
                color_idx = (int(val * 12) + self.color_offset) % 24
                
                # draw big pixel block
                px = x * self.pixel_size
                py = y * self.pixel_size
                
                for dy in range(self.pixel_size):
                    for dx in range(self.pixel_size):
                        if px + dx < 160 and py + dy < 128:
                            d.pset(px + dx, py + dy, color_idx)


class SimpleWaveDemo(sprog.Sprog):
    def init(self):
        self.time = 0
        self.colors = [4, 5, 6, 9, 10, 11, 13, 14, 15]  # nice gradient
    
    def update(self):
        self.time += 0.05
    
    def draw(self):
        d = self.display
        d.cls(0)
        
        # just draw some flowing lines - way faster
        for y in range(0, 128, 8):  # every 8 pixels
            wave = int(30 * math.sin(y * 0.1 + self.time)) + 80
            color_idx = int((y + self.time * 20) / 16) % len(self.colors)
            color = self.colors[color_idx]
            
            # draw thick flowing line
            for x in range(max(0, wave - 3), min(160, wave + 4)):
                for dy in range(6):
                    if y + dy < 128:
                        d.pset(x, y + dy, color)


class TunnelDemo(sprog.Sprog):
    def init(self):
        self.time = 0
        self.center_x = 80
        self.center_y = 64
        
    def update(self):
        self.time += 0.08
    
    def draw(self):
        d = self.display
        d.cls(0)
        
        # tunnel effect with big pixels for speed
        for y in range(0, 128, 4):
            for x in range(0, 160, 4):
                # distance from center
                dx = x - self.center_x
                dy = y - self.center_y
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist > 0:
                    # tunnel effect
                    tunnel = int(dist * 0.5 - self.time * 10) % 24
                    
                    # draw 4x4 block
                    for py in range(4):
                        for px in range(4):
                            if x + px < 160 and y + py < 128:
                                d.pset(x + px, y + py, tunnel)


# this one should be smooth even at 125MHz
game = SimpleWaveDemo()  # or FastPlasmaDemo() or TunnelDemo()
game.run()