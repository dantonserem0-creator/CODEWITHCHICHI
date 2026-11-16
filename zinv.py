import pygame
import math

pygame.init()

WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Mouse water ripple")

clock = pygame.time.Clock()

ripples = []

running = True

while running:

    clock.tick(60)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEMOTION:
            ripples.append([event.pos, 1])

    screen.fill((10, 20, 35))

    new_ripples = []

    for pos, radius in ripples:

        if radius < 180:

            alpha = max(0, 255 - radius)

            surface = pygame.Surface((400,400),pygame.SRCALPHA)

            pygame.draw.circle(
                surface,
                (80, 180, 255,radius),
                (200,200),
                int(radius),
                2
            )

            screen.blit(
                surface,
                (pos[0]-200, pos[1]-200),
            )

            new_ripples.append([pos, radius+3])

    ripples = new_ripples

    pygame.display.flip()

pygame.quit()
