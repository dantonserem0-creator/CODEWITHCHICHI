import pygame, math, random, colorsys

pygame.init()
W, H = 720, 1280
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("Cosmic Energy Bloom")
clock = pygame.time.Clock()
cx, cy = W // 2, H // 2
random.seed(42)
stars = [(random.randrange(W), random.randrange(H), random.random() * 1.8 + 0.4) for x in range(180)]
particles = []
font = pygame.font.SysFont("consolas", 22, bold=True)
small = pygame.font.SysFont("consolas", 13)
start = pygame.time.get_ticks()
running = True


def rainbow(t):
    c = colorsys.hsv_to_rgb(t % 1, 0.9, 1)
    return tuple(int(v * 255) for v in c)


def curve_points(scale, petals, phase, twist, count=500):
    pts = []
    for i in range(count):
        t = math.tau * i / (count - 1)
        r = scale * (0.42 + 0.58 * abs(math.cos(petals * t / 2)) ** 1.5)
        r *= 0.78 + 0.22 * math.cos(twist * t + phase)
        a = t + phase
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def draw_curve(points, col, width=1):
    if len(points) > 1:
        pygame.draw.aalines(screen, col, True, points)


while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    ms = pygame.time.get_ticks() - start
    t = ms / 100
    progress = (ms % 10000) / 18000
    grow = min(1, progress * 4.5)
    screen.fill((3, 4, 15))

    for x, y, s in stars:
        pulse = 0.5 + 0.5 * math.sin(t * 2 + s)
        col = (int(35 + 35 * pulse), int(50 + 70 * pulse), int(110 + 120 * pulse))
        pygame.draw.circle(screen, col, (x, y), max(1, int(s * pulse)))

    for i in range(7):
        radius = (14 + i * 15) * grow
        col = rainbow(t * 0.04 + i * 0.11)
        pygame.draw.circle(screen, col, (cx, cy), int(radius), 1)

    for layer in range(8):
        scale = (45 + layer * 27) * grow
        petals = 6 + layer % 4 * 2
        phase = t * (0.25 + layer * 0.025) * (1 if layer % 2 else -1)
        pts = curve_points(scale, petals, phase, 3 + layer % 3)
        col = rainbow(t * 0.055 + layer * 0.105)
        draw_curve(pts, col)
        if layer % 2 == 0:
            for j in range(0, len(pts), 25):
                x, y = pts[j]
                pygame.draw.circle(screen, col, (int(x), int(y)), 2)

    for layer in range(5):
        scale = (35 + layer * 21) * grow
        pts = []
        for i in range(600):
            a = math.tau * i / 599
            r = scale * (1 + 0.38 * math.sin(9 * a + 1.3 + layer))
            r += 9 * math.sin(15 * a - t * 0.8)
            pts.append((cx + math.cos(a + layer * 0.16) * r,
                        cy + math.sin(a + layer * 0.16) * r))
        draw_curve(pts, rainbow(t * 0.06 + layer * 0.17))

    for i in range(24):
        a = i * math.tau / 24 + t * 0.22
        r = (100 + 30 * math.sin(t * 1.4 + i)) * grow
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r
        col = rainbow(i / 24 + t * 0.05)
        pygame.draw.circle(screen, col, (int(x), int(y)), 5)
        pygame.draw.circle(screen, (255, 255, 255), (int(x), int(y)), 2)

    if random.random() > 0.45:
        a = random.random() * math.tau
        speed = random.uniform(35, 130)
        particles.append([cx, cy, math.cos(a) * speed, math.sin(a) * speed,
                          random.uniform(1.0, 2.8), random.random()])

    for p in particles[:]:
        p[0] += p[2] / 30
        p[1] += p[3] / 30
        p[4] -= 0.025
        if p[4] <= 0:
            particles.remove(p)
            continue
        col = rainbow(p[5] + t * 0.1)
        pygame.draw.circle(screen, col, (int(p[0]), int(p[1])),
                           max(1, int(p[4])))

    for i in range(12):
        a = i * math.tau / 12 - t * 0.18
        r = 225 * grow
        x = cx + math.cos(a) * r
        y = cy + math.sin(a) * r
        col = rainbow(i / 12 + t * 0.04)
        pygame.draw.circle(screen, col, (int(x), int(y)), 3)

    for i in range(4):
        radius = (5 + i * 5) * (1 + 0.18 * math.sin(t * 3 + i))
        pygame.draw.circle(screen, rainbow(t * 0.12 + i * 0.2),
                           (cx, cy), int(radius), 1)

    title = font.render("COSMIC ENERGY BLOOM", True, (220, 225, 255))
    subtitle = small.render("GENERATIVE SACRED GEOMETRY", True, (140, 155, 200))
    screen.blit(title, title.get_rect(center=(cx, 1090)))
    screen.blit(subtitle, subtitle.get_rect(center=(cx, 1120)))

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
