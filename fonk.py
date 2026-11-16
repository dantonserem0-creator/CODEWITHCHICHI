import pygame
import random
import math

pygame.init()

WIDTH, HEIGHT = 900, 1600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Advanced Python Animation")

clock = pygame.time.Clock()


class Particle:

    def __init__(self):
        self.x = random.randint(0, WIDTH)
        self.y = random.randint(0, HEIGHT)
        self.radius = random.randint(2, 6)
        self.speed = random.uniform(1, 4)
        self.angle = random.uniform(0, math.pi * 2)
        self.color = (
            random.randint(50, 255),
            random.randint(50, 255),
            random.randint(50, 255),
        )

    def move(self, t):
        self.x += math.cos(self.angle + t * 0.01) * self.speed
        self.y += math.sin(self.angle + t * 0.01) * self.speed

        if self.x < 0 or self.x > WIDTH:
            self.angle = math.pi - self.angle

        if self.y < 0 or self.y > HEIGHT:
            self.angle = -self.angle

    def draw(self):
        pygame.draw.circle(
            screen, self.color, (int(self.x), int(self.y)), self.radius
        )


particles = []
for _ in range(250):
    particles.append(Particle())

running = True
frame = 0

while running:
    screen.fill((5, 5, 15))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    for i in range(len(particles)):
        p1 = particles[i]
        p1.move(frame)
        p1.draw()

        for j in range(i + 1, len(particles)):
            p2 = particles[j]
            dist = math.hypot(p1.x - p2.x, p1.y - p2.y)

            if dist < 120:
                alpha = max(0, 255 - int(dist * 2))
                color = (
                    alpha % 255,
                    (alpha * 2) % 255,
                    (alpha * 3) % 255,
                )
                pygame.draw.line(
                    screen, color, (int(p1.x), int(p1.y)), (int(p2.x), int(p2.y))
                )

    pulse_radius = abs(math.sin(frame * 0.02)) * 180
    pygame.draw.circle(
        screen, (100, 200, 255), (WIDTH // 2, HEIGHT // 2), int(pulse_radius), 3
    )

    pygame.display.flip()
    clock.tick(60)
    frame += 1

pygame.quit()
