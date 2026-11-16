import random

import pygame
from numba.core.cgutils import false_bit

pygame.init()
W, H = 1000, 650
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("city from blueprint")
clock = pygame.time.clock()

random.seed(4)

stage = 0
start = pygame.time.get_ticks()
building = 0
road_progress = 0

build_data = (
(95, 360, 90, 140),
(220, 285, 100, 215),
(355, 335, 80, 165),
(475, 225, 110, 275),
(620, 305, 95, 195),
(755, 195, 110, 305),
)

cars = [
    [60, 0, 2.5],
    [300, 0, 2.0],
    [500, 0, 2.7],
    [800, 0, 2.2],
]

def ease(t):
    t = max(0, min(1, t))
    return t * t * (3 - 2 * t)

def background():
    screen.fill((5, 9, 16))

    for y in range(0, 500, 40):
        pygame.draw.line(screen, (9, 17, 26), (0, y), (W, y), 1)

    pygame.draw.rect(screen, (8, 20, 25), (0, 500, W, 150))

def building(index, p=1):
    x, top, w, h = build_data[index]
    current_h = h * p
    y = 500 - current_h

    pygame.draw.rect(screen, ( 43, 49, 59),
                     (x, y, w, current_h ), 2)

    floors = max (1, int(current_h / 28))

    for f in range(floors):
        wy = y + 10 + f * 28

        for wx in range(int(x + 10), int(x + w - 8), 19):
            if wy + 13 < 500:
                pygame.draw.rect(screen, (85, 150, 175),
                                 (wx, wy, 18, 13))

def final_windows():
    for x, top, w, h in build_data:
        for yy in range(int(500 -h+10), 490, 28):
            for xx in range(int(x+10), int(x+w-8), 19):
                if random.random() > .22:
                    pygame.draw.rect(screen, (215, 180, 85),
                                     (xx, yy, 10, 13))

def road(p=1):
    road_y = int(520 + 35 * (1-p))

    pygame.draw.polygon(
        screen,
        (31, 34, 39),
        [(0, road_y), (W, road_y-18),
        (W, 650), (0, 650)]
    )

    pygame.draw.line(screen, (screen, (82, 87, 94),
                              (0, road_y),
                              (W, road_y-18), 5),

    pygame.draw.line(screen, (285, 185, 75),
                     (0, road_y+55),
                     (W, road_y+37), 4)

    for x in range(20,W, 70):
        yy = road_y + 27 - int(x * 18 / W)
        pygame.draw.line(screen, (210, 190, 80),
                         (x, yy), (x+32, yy-1), 4)

def street_lights():
        for x in range(70, 950, 90):
            y = int(520 - x * 18 / W)

            pygame.draw.line(screen, (125, 130, 138),
                             (x, y), (x,y-48), 3)

            pygame.draw.circle(screen, (245,210,105),
                               (x, y-51), 6)

def cars_move():
    for car in cars:
        car[0] += car[2]

        if car [0] > W + 40:
            car[0] = -50

        x = int(car[0])
        y = int(520 - x * 18 / W)

        pygame.draw.rect(screen, (155, 160, 168),
                         (x, y-12, 36, 11))

        pygame.draw.rect(screen, (65, 75, 85),
                         (x+7, y-18, 20, 7))

        pygame.draw.circle(screen, (18,20,23),
                           (x+8,y), 5)

        pygame.draw.circle(screen, (18, 20, 23),
                           (x+29,y), 5)

        def main():
            global stage, start, buildings, road_progress

            running = True

            while running:
                clock.tick(60)

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False

                t = (pygame.time.get_ticks() - start) / 1000

                if stage == 0:
                    if t > .65:
                        buildings += 1
                        start = pygame.time.get_ticks()

                        if buildings >= len(build_data):
                            stage = 1
                            start = pygame.time.get_ticks()

        elif stage == 1:
            road_progress = min(t / 2.5, 1)

            if t > 3:
                stage = 2
                start = pygame.time.get_ticks()

        elif stage == 2:
            if t > 1:
                stage = 3
                start = pygame.time.get_ticks()

        elif stage == 3:
            if t > 8:
                stage = 0
                buildings 0
                road_progress = 0
                start = pygame.time.get_ticks()

        background()

        for i in range(buildings):
            buildings(i)

        if stage == 0 and buildings < len (build_data):
            p = ease(min(t/.65, 1))
            building(buildings, p)

        if buildings >= 1:
            final_windows()

        if stage >= 2:
            street_lights()

        if stage >= 3:
            cars_move()

        pygame.display.flip()

pygame.quit()












