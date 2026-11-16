import pygame
import math
import colorsys
import random

pygame.init()

W, H = 720, 1280
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Fractal Flame Explosion")
clock = pygame.time.Clock()
cx, cy = W // 2, H // 2

font = pygame.font.SysFont("consolas", 22, bold=True)
small = pygame.font.SysFont("consolas", 13)

random.seed(31)
# Fixed tuple unpacking: 3 values (x, y, size) using random.random()
stars = [
    (random.randrange(W), random.randrange(H), random.random() * 2 + 0.5)
    for _ in range(100)
]

start = pygame.time.get_ticks()
running = True


def rainbow(v):
    # Fixed parameter name (v), module name (colorsys), and boosted saturation (0.85)
    return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(v % 1.0, 0.85, 1.0))


def branch(x, y, angle, length, depth, t, progress):
    if depth == 0 or length < 2 or progress <= 0:
        return

    length *= min(1.0, progress * 1.8)
    bend = math.sin(t * 1.2 + depth * 0.8) * 0.09

    # Fixed branching angles so branches split left (-0.42) and right (+0.42)
    a1 = angle + 0.42 + bend
    a2 = angle - 0.42 + bend

    ex = x + math.cos(angle) * length
    ey = y + math.sin(angle) * length

    col = rainbow(t * 0.035 + depth * 0.085 + angle * 0.08)

    # Fixed pygame.draw.line arguments and line thickness
    pygame.draw.line(screen, col, (int(x), int(y)), (int(ex), int(ey)), max(1, depth // 2))
    pygame.draw.circle(screen, col, (int(ex), int(ey)), depth)

    if depth > 2:
        pygame.draw.circle(screen, (100, 170, 255), (int(ex), int(ey)), max(1, depth // 2))

    # Fixed syntax error (0..75 -> 0.075)
    child_progress = progress - 0.075
    branch(ex, ey, a1, length * 0.73, depth - 1, t, child_progress)
    branch(ex, ey, a2, length * 0.73, depth - 1, t, child_progress)


def crystal(cx, cy, radius, sides, phase, col):
    pts = []
    for i in range(sides):
        a = i * math.tau / sides + phase
        r = radius * (0.75 + 0.22 * math.sin(i * 2 + phase))
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    pygame.draw.polygon(screen, col, pts, 1)


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    t = (pygame.time.get_ticks() - start) / 1000.0
    cycle = (t % 18) / 18.0
    growth = min(1.0, cycle * 3.5)

    screen.fill((3, 4, 17))

    # Draw twinkling background stars
    for x, y, s in stars:
        pulse = 0.5 + 0.5 * math.sin(t * 2 + s)
        col = (int(35 + 50 * pulse), int(50 + 60 * pulse), int(100 + 120 * pulse))
        pygame.draw.circle(screen, col, (x, y), max(1, int(s * pulse)))

    # Draw 8-way recursive fractal branches
    for i in range(8):
        a = i * math.tau / 8 + t * 0.12
        branch(cx, cy, a, 115 * growth, 8, t + i * 0.1, growth + 0.1)

    # Draw rotating geometric crystal layers
    for layer in range(5):
        radius = (35 + layer * 33) * growth
        sides = 8 + layer * 4
        # Fixed typo: used '1' instead of 'i' for alternating rotation direction
        phase = t * 0.16 * (1 if layer % 2 else -1)
        col = rainbow(t * 0.035 + layer * 0.15)
        if radius > 1:
            crystal(cx, cy, radius, sides, phase, col)

    # Draw orbiting energy nodes
    for i in range(16):
        a = i * math.tau / 16 + t * 0.17
        r = (65 + 25 * math.sin(t * 2 + i)) * growth
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r
        col = rainbow(i / 16 + t * 0.08)
        pygame.draw.circle(screen, col, (int(x), int(y)), 4)
        pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 1)

    # Completed unfinished core rings loop
    for i in range(3):
        radius = int((8 + i * 8) * (1 + 0.25 * math.sin(t * 3 + i)))
        pygame.draw.circle(screen, rainbow(t * 0.12 + i * 0.25), (cx, cy), max(1, radius), 2)

    # Fixed incomplete RGB tuple, typos ('cenetr', 'bilt'), and text Y-positions so they don't overlap
    title = font.render("FRACTAL FLAME", True, (220, 230, 255))
    subtitle = small.render("RECURSIVE GEOMETRY / PYTHON", True, (110, 150, 210))
    screen.blit(title, title.get_rect(center=(cx, 1080)))
    screen.blit(subtitle, subtitle.get_rect(center=(cx, 1110)))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
