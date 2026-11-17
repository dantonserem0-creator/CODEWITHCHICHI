import turtle
import colorsys


def draw_flare():
    screen = turtle.Screen()
    screen.bgcolor('black')
    screen.setup(width=800, height=600)
    screen.title("Solar Flare")
    screen.tracer(1)

    t = turtle.Turtle()
    t.speed(0)
    t.hideturtle()

    hue = 0.8
    t.penup()
    t.goto(0, 0)
    t.pendown()

    for i in range(250):
        # Wrap the hue value with % 1.0 and pass 3 arguments (H, S, V)
        color = colorsys.hsv_to_rgb(hue % 1.0, 0.9, 1.0)
        t.pencolor(color)
        hue += 0.005

        t.pensize(i / 100)
        t.forward(i * 1.2)
        t.left(60)
        t.forward(i * 0.5)
        t.right(120)
        t.right(121)

    screen.mainloop()


draw_flare()
