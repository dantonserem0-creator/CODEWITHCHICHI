import pygame, math, colorsys

pygame.init()
W, H = 720, 1280
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Rainbow Harmonic Waves")
clock = pygame.time.Clock()
cx, cy = W // 2, H // 2
font = pygame.font.SysFont("consolas", 21, bold=True)
small = pygame.font.SysFont("consolas", 13)
running = True
start = pygame.time.get_ticks()


def rgb(h):
    c = colorsys.hsv_to_rgb(h % 1, 0.9, 1)
    return tuple(int(v * 255) for v in c)


def wave_points(t, layer, growth):
    pts = []
    phase = t * 0.65 + layer * 0.19
    for i in range(900):
        a = math.tau * i / 899
        r = growth * (
            75
            + 36 * math.sin(7 * a + phase)
            + 24 * math.cos(11 * a - phase * 1.3)
            + 15 * math.sin(17 * a + phase * 0.7)
        )
        twist = 0.32 * math.sin(3 * a + phase)
        x = r * math.cos(a + twist)
        y = r * math.sin(a + twist)
        pts.append((cx + x, cy + y))
    return pts


def lissajous(t, index, growth):
    pts = []
    phase = index * math.tau / 18
    for i in range(700):
        a = math.tau * i / 699
        x = 220 * math.sin(3 * a + t * 0.5 + phase)
        y = 300 * math.sin(4 * a - t * 0.38 + phase)
        rot = t * 0.08
        xx = x * math.cos(rot) - y * math.sin(rot)
        yy = x * math.sin(rot) + y * math.cos(rot)
        pts.append((cx + xx * growth, cy + yy * growth))
    return pts


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    t = (pygame.time.get_ticks() - start) / 1000
    cycle = (t % 16) / 16
    growth = min(1, cycle * 4 + 0.08)
    screen.fill((3, 4, 17))

    for i in range(14):
        radius = 18 + i * 27
        pulse = 1 + 0.025 * math.sin(t * 2 + i)
        pygame.draw.circle(
            screen, (12, 20, 48),
            (cx, cy), int(radius * pulse), 1
        )

    for layer in range(9):
        pts = wave_points(t, layer, growth)
        col = rgb(t * 0.045 + layer / 9)
        pygame.draw.aalines(screen, col, True, pts)

    for i in range(18):
        pts = lissajous(t, i, growth)
        col = rgb(t * 0.035 + i / 18)
        pygame.draw.aalines(screen, col, True, pts)

    for i in range(36):
        a = i * math.tau / 36 + t * 0.2
        r = (100 + 95 * (0.5 + 0.5 * math.sin(t * 1.4 + i))) * growth
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r
        col = rgb(i / 36 + t * 0.06)
        pygame.draw.circle(screen, col, (int(x), int(y)), 4)
        pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 1)

    for i in range(5):
        radius = int((8 + i * 8) * (1 + 0.2 * math.sin(t * 3 + i)))
        pygame.draw.circle(
            screen, rgb(t * 0.1 + i * 0.2),
            (cx, cy), radius, 1
        )

    title = font.render("HARMONIC WAVES", True, (220, 230, 255))
    subtitle = small.render("PHASE-LOCKED LISSAJOUS FIELD", True, (140, 160, 210))
    screen.blit(title, title.get_rect(center=(cx, 1090)))
    screen.blit(subtitle, subtitle.get_rect(center=(cx, 1120)))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
