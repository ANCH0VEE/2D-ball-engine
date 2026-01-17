# Simple Pygame 2D Ball Engine:
- A simple ball engine to simulate collisions between circular entities.

[![Watch the video on YouTube](https://img.youtube.com/vi/R0Lih2EsF6E/hqdefault.jpg)](https://youtu.be/R0Lih2EsF6E)

## Features:
- Smooth vector-based movement and momentum-like behavior.
- Ball collision response.
- Variables for desired movement type and collision response:
    - friction
    - restitution (bounciness)
    - repel_speed_percentage (fluid repulsion of balls that collide instead of instant displacement of overlapping balls)
- Scrolling movement of player.
- Grid background.
- Direction and acceleration vector visualizations.
- Entity count and frame rate displayed at top left.
- Optimization:
    - Filters out off-screen balls, so only on-screen ones are rendered.
    - Uses spatial hashing to reduce the brute-force O(n^2) running time of collision resolution (quadratic growth in run time for every new ball created: problematic in large numbers without optimization).
        - Partitions map into grid cells of side length of largest ball's diameter.
        - Checks collisions normally, but with a smaller group that consists only of balls contained within neighboring grid cells.
        - Better performance with larger ball quantities, especially when smaller and more spread out. Balls too large still cause significant increase in run-time.

## Instructions:
- WASD or arrow keys to move the "player."
- Entity clearing: "C".
- Create ball template (outline) with left mouse button, hold until ball outline reaches desired size, release to spawn ball.
