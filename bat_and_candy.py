# bat_and_candy.py
"""
Bat & Candy - A Flappy-Bird-like game using pygame.
- Controls:
    Space / Left Mouse: flap
    P: pause / resume
    R: restart after game over
    ESC / Close window: quit
- Files:
    highscore.txt will be created in the same folder to save best score.
"""

import pygame
import sys
import random
import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundles."""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, relative_path)

# ---------- Configuration ----------
SCREEN_WIDTH = 680
SCREEN_HEIGHT = 900
FPS = 60

GRAVITY = 0.48
FLAP_STRENGTH = -9.5
OBSTACLE_SPEED_START = 3.0
OBSTACLE_GAP = 380  # vertical gap height between top & bottom columns
OBSTACLE_DISTANCE = 230  # horizontal distance between consecutive obstacles
OBSTACLE_WIDTH = 78
CANDY_SPAWN_CHANCE = 0.75  # chance to spawn a candy with an obstacle
DIFFICULTY_INCREASE_RATE = 0.00000025  # how quickly speed ramps up per frame

HIGHSCORE_FILE = "highscore.txt"
def load_highscore():
    path = resource_path(HIGHSCORE_FILE)
    if not os.path.exists(path):
        return 0
    try:
        with open(path, "r") as f:
            return int(f.read().strip() or 0)
    except Exception:
        return 0

def save_highscore(score):
    path = resource_path(HIGHSCORE_FILE)
    try:
        with open(path, "w") as f:
            f.write(str(int(score)))
    except Exception:
        pass
 
# Colors
WHITE = (255, 255, 255)
BLACK = (16, 16, 16)
BG_COLOR = (15, 24, 40)
BAT_COLOR = (40, 200, 200)
CANDY_COLOR = (255, 120, 120)
OBSTACLE_COLOR = (80, 170, 90)
TEXT_COLOR = (230, 230, 230)

# ---------- Utilities ----------
def load_highscore():
    if not os.path.exists(HIGHSCORE_FILE):
        return 0
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip() or 0)
    except Exception:
        return 0

def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(int(score)))
    except Exception:
        pass

# ---------- Sprite / Game Object Classes ----------
class Bat(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.orig_image = self.make_bat_surface(56, 40)
        self.image = self.orig_image
        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
        self.vel = 0.0
        self.angle = 0.0  # for tilting sprite

    @staticmethod
    def make_bat_surface(w, h):
        """Draws a simple stylized bat on a transparent surface."""
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # body (ellipse)
        pygame.draw.ellipse(surf, BAT_COLOR, (w*0.15, h*0.20, w*0.7, h*0.6))
        # wings
        pygame.draw.polygon(surf, BAT_COLOR, [(0, h*0.5), (w*0.15, h*0.2), (w*0.15, h*0.8)])
        pygame.draw.polygon(surf, BAT_COLOR, [(w, h*0.5), (w*0.85, h*0.2), (w*0.85, h*0.8)])
        # little face
        pygame.draw.circle(surf, BLACK, (int(w*0.55), int(h*0.45)), 3)
        pygame.draw.circle(surf, BLACK, (int(w*0.45), int(h*0.45)), 3)
        return surf

    def update(self, dt):
        # physics
        self.vel += GRAVITY * dt
        self.rect.y += int(self.vel * dt)

        # tilt logic: upward = rotate up, downward = rotate down
        target_angle = max(-25, min(25, -self.vel * 2.0))
        # smooth interpolation
        self.angle += (target_angle - self.angle) * 0.12

        # rotate image
        self.image = pygame.transform.rotozoom(self.orig_image, self.angle, 1.0)
        self.rect = self.image.get_rect(center=self.rect.center)
        self.mask = pygame.mask.from_surface(self.image)

    def flap(self):
        self.vel = FLAP_STRENGTH

class Obstacle(pygame.sprite.Sprite):
    def __init__(self, x, gap_y, width, gap_height, speed):
        super().__init__()
        self.x = x
        self.width = width
        self.gap_y = gap_y
        self.gap_height = gap_height
        self.speed = speed
        # top rect: from top to gap start
        self.top_rect = pygame.Rect(self.x, 0, self.width, max(0, self.gap_y - self.gap_height // 2))
        # bottom rect: from gap end to bottom
        bottom_y = self.gap_y + self.gap_height // 2
        self.bottom_rect = pygame.Rect(self.x, bottom_y, self.width, SCREEN_HEIGHT - bottom_y)
        # scoring flag: prevent multiple scores
        self.passed = False

    def update(self, dt):
        dx = int(self.speed * dt)
        self.x -= dx
        self.top_rect.x = self.x
        self.bottom_rect.x = self.x

    def draw(self, surf):
        # a little candy-wrapper-ish column with a rounded top
        # top column
        pygame.draw.rect(surf, OBSTACLE_COLOR, self.top_rect)
        # bottom column
        pygame.draw.rect(surf, OBSTACLE_COLOR, self.bottom_rect)

    def offscreen(self):
        return self.x + self.width < -50

    def collides_with(self, sprite_mask, sprite_offset):
        # convert rects to surfaces to use masks or do simpler rect collision
        # We'll use rect collision then refined mask if necessary
        # get sprite rect at its current position using sprite_offset
        sprite_rect = sprite_mask.get_rect()
        sx, sy = sprite_offset
        sprite_rect.topleft = (sx, sy)
        # simple rectangle collision check:
        if sprite_rect.colliderect(self.top_rect) or sprite_rect.colliderect(self.bottom_rect):
            return True
        return False

class Candy(pygame.sprite.Sprite):
    def __init__(self, x, y, size=20, speed=3.0):
        super().__init__()
        self.size = size
        self.image = self.make_candy_surface(size)
        self.rect = self.image.get_rect(center=(x, y))
        self.mask = pygame.mask.from_surface(self.image)
        self.speed = speed
        self.collected = False

    @staticmethod
    def make_candy_surface(size):
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        cx = size // 2
        cy = size // 2
        # round candy center
        pygame.draw.circle(surf, CANDY_COLOR, (cx, cy), int(size*0.36))
        # little wrappers
        wing_w = int(size*0.3)
        wing_h = int(size*0.12)
        pygame.draw.rect(surf, CANDY_COLOR, (0, cy-wing_h//2, wing_w, wing_h))
        pygame.draw.rect(surf, CANDY_COLOR, (size-wing_w, cy-wing_h//2, wing_w, wing_h))
        # highlight
        pygame.draw.circle(surf, (255, 200, 200), (int(cx - size*0.12), int(cy - size*0.12)), max(1, int(size*0.08)))
        return surf

    def update(self, dt):
        self.rect.x -= int(self.speed * dt)

    def offscreen(self):
        return self.rect.right < -20

# ---------- Game Class ----------
class BatCandyGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Bat & Candy")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.big_font = pygame.font.Font(None, 64)

        self.highscore = load_highscore()

        self.reset()

    def reset(self):
        # reset gameplay state
        self.bat = Bat(int(SCREEN_WIDTH*0.28), SCREEN_HEIGHT//2)
        self.obstacles = []
        self.candies = pygame.sprite.Group()
        self.score = 0
        self.running = True
        self.playing = False  # becomes True when first flap
        self.game_over = False
        self.spawn_x = SCREEN_WIDTH + 50
        self.spawn_timer = 0.0
        self.speed = OBSTACLE_SPEED_START
        self.frames = 0

        # initial obstacle so player has some time before first challenge
        # but not too many
        first_gap_y = SCREEN_HEIGHT // 2
        self.push_obstacle(first_gap_y, x=SCREEN_WIDTH + 60)

    def push_obstacle(self, gap_y, x=None):
        if x is None:
            x = self.spawn_x
            self.spawn_x += OBSTACLE_DISTANCE
        obs = Obstacle(x, gap_y, OBSTACLE_WIDTH, OBSTACLE_GAP, self.speed)
        self.obstacles.append(obs)
        # sometimes spawn candy in gap center
        if random.random() < CANDY_SPAWN_CHANCE:
            candy_y = gap_y + random.randint(-int(OBSTACLE_GAP*0.25), int(OBSTACLE_GAP*0.25))
            candy = Candy(x + OBSTACLE_WIDTH//2, candy_y, size=20, speed=self.speed)
            self.candies.add(candy)

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return
                if event.key == pygame.K_SPACE:
                    self.on_flap()
                if event.key == pygame.K_p:
                    # pause toggle
                    self.playing = not self.playing if not self.game_over else self.playing
                if event.key == pygame.K_r and self.game_over:
                    self.reset()
                if event.key == pygame.K_RETURN and not self.playing and not self.game_over:
                    # allow enter to start too
                    self.on_flap()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self.on_flap()

    def on_flap(self):
        if not self.playing and not self.game_over:
            self.playing = True
        if not self.game_over:
            self.bat.flap()

    def update(self, dt):
        if not self.playing or self.game_over:
            return

        # increase difficulty slowly
        self.frames += 1
        self.speed += DIFFICULTY_INCREASE_RATE * dt

        # update bat with dt scaled to 60fps baseline
        tscale = dt / (1000.0 / FPS) * 1.0  # dt is in ms
        self.bat.update(tscale)

        # spawn obstacles periodically by using spawn_x spacing
        # ensure there's always at least two ahead
        while len(self.obstacles) < 4:
            # generate a gap y with some randomness but keeps inside screen
            min_y = int(OBSTACLE_GAP * 0.6)
            max_y = SCREEN_HEIGHT - min_y
            gap_y = random.randint(min_y, max_y)
            self.push_obstacle(gap_y)

        # update obstacles
        for obs in list(self.obstacles):
            obs.speed = self.speed
            obs.update(tscale)
            # check for passing for scoring
            if not obs.passed and (obs.x + obs.width) < self.bat.rect.centerx:
                obs.passed = True
                self.score += 1
            if obs.offscreen():
                self.obstacles.remove(obs)

        # update candies
        for candy in list(self.candies):
            candy.speed = self.speed
            candy.update(tscale)
            if candy.offscreen():
                self.candies.remove(candy)

        # collision checks
        # 1) with obstacles (rect collision)
        for obs in self.obstacles:
            # check rectangular overlap first
            if self.bat.rect.colliderect(obs.top_rect) or self.bat.rect.colliderect(obs.bottom_rect):
                self.game_over = True
                break
        # 2) with screen top/bottom
        if self.bat.rect.top <= 0 or self.bat.rect.bottom >= SCREEN_HEIGHT:
            self.game_over = True

        # 3) candy collisions (mask-based)
        for candy in list(self.candies):
            offset = (candy.rect.left - self.bat.rect.left, candy.rect.top - self.bat.rect.top)
            # masks: get masks
            if self.bat.mask.overlap(candy.mask, offset):
                # collect
                self.score += 5  # candy bonus
                self.candies.remove(candy)

        if self.game_over:
            # save highscore if needed
            if self.score > self.highscore:
                self.highscore = self.score
                save_highscore(self.highscore)

    def draw_hud(self):
        # score top-left
        score_surf = self.font.render(f"Score: {self.score}", True, TEXT_COLOR)
        self.screen.blit(score_surf, (12, 12))
        hs_surf = self.font.render(f"Best: {self.highscore}", True, TEXT_COLOR)
        self.screen.blit(hs_surf, (12, 44))

    def draw(self):
        self.screen.fill(BG_COLOR)

        # background simple gradient-ish (vertical)
        for i in range(0, SCREEN_HEIGHT, 24):
            shade = max(0, min(40, 40 - i//20))
            pygame.draw.rect(self.screen, (12+shade, 20+shade, 36+shade), (0, i, SCREEN_WIDTH, 24))

        # draw obstacles
        for obs in self.obstacles:
            obs.draw(self.screen)

        # draw candies
        for candy in self.candies:
            self.screen.blit(candy.image, candy.rect)

        # draw bat
        self.screen.blit(self.bat.image, self.bat.rect)

        # HUD
        self.draw_hud()

        # overlays
        if not self.playing and not self.game_over:
            # start screen hint
            title = self.big_font.render("Bat & Candy", True, TEXT_COLOR)
            sub = self.font.render("Press SPACE or click to flap — collect candies!", True, TEXT_COLOR)
            w = title.get_width()
            self.screen.blit(title, ((SCREEN_WIDTH - w) // 2, SCREEN_HEIGHT // 2 - 120))
            self.screen.blit(sub, ((SCREEN_WIDTH - sub.get_width()) // 2, SCREEN_HEIGHT // 2 - 60))
        if self.game_over:
            over = self.big_font.render("Game Over", True, TEXT_COLOR)
            sc = self.font.render(f"Final Score: {self.score}", True, TEXT_COLOR)
            r = self.font.render("Press R to play again", True, TEXT_COLOR)
            self.screen.blit(over, ((SCREEN_WIDTH - over.get_width()) // 2, SCREEN_HEIGHT // 2 - 90))
            self.screen.blit(sc, ((SCREEN_WIDTH - sc.get_width()) // 2, SCREEN_HEIGHT // 2 - 20))
            self.screen.blit(r, ((SCREEN_WIDTH - r.get_width()) // 2, SCREEN_HEIGHT // 2 + 30))

        # pause hint
        if self.playing and not self.game_over:
            pause_hint = self.font.render("P to Pause", True, TEXT_COLOR)
            self.screen.blit(pause_hint, (SCREEN_WIDTH - pause_hint.get_width() - 12, 12))

        pygame.display.flip()

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS)  # ms since last frame
            self.handle_input()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()


# ---------- Entry Point ----------
if __name__ == "__main__":
    game = BatCandyGame()
    game.run()
