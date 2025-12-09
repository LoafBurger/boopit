import pygame
import random
import math
import sys

pygame.init()

# -------- Window Setup --------
WIDTH, HEIGHT = 1100, 800
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Boopit")

# -------- Colors (Sci-Fi Theme) --------
BG = (5, 10, 20)
PLAYER_CORE = (0, 180, 255)
PLAYER_GLOW = (0, 120, 200)
BULLET_COLOR = (200, 240, 255)
ENEMY_CORE = (255, 40, 80)
ENEMY_GLOW = (80, 10, 20)
HUD_COLOR = (150, 200, 255)
POWER_SPEED_COLOR = (0, 220, 255)

# -------- Player Settings --------
PLAYER_BASE_SPEED = 5
PLAYER_SIZE = 38

# -------- Enemy Settings --------
ENEMY_SIZE = 34
ENEMY_SPEED = 2.3
SPAWN_RATE = 600  # ms

# -------- Bullet Settings --------
BULLET_SPEED = 11
BULLET_SIZE = 6

# -------- Power-Up Settings --------
POWERUP_SIZE = 30
POWERUP_SPAWN_RATE = 7000   # ms between spawns
POWERUP_DURATION = 5000     # ms duration
POWERUP_TYPES = ["speed"]   # wave removed

# -------- Dash Settings --------
DASH_DISTANCE = 220
DASH_COOLDOWN = 1000  # ms

clock = pygame.time.Clock()
font = pygame.font.SysFont("bahnschrift", 28)

# -------- Game States --------
MENU, PLAYING, END = "menu", "playing", "end"


def draw_text(text, x, y, color=HUD_COLOR, center=True):
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    WIN.blit(surf, rect)


def angle_to(target, origin):
    dx = target[0] - origin[0]
    dy = target[1] - origin[1]
    return math.degrees(math.atan2(dy, dx))


# -------- Parallax Background --------
def init_stars(count=160):
    stars = []
    for _ in range(count):
        layer = random.choice([1, 2, 3])
        if layer == 1:
            speed = 0.3
            size = 1
            color = (20, 40, 80)
        elif layer == 2:
            speed = 0.6
            size = 2
            color = (40, 80, 140)
        else:
            speed = 1.0
            size = 3
            color = (80, 140, 220)
        stars.append({
            "x": random.randint(0, WIDTH),
            "y": random.randint(0, HEIGHT),
            "speed": speed,
            "size": size,
            "color": color,
        })
    return stars


def update_and_draw_background(stars):
    WIN.fill(BG)
    for s in stars:
        s["y"] += s["speed"]
        if s["y"] > HEIGHT:
            s["y"] = 0
            s["x"] = random.randint(0, WIDTH)
        pygame.draw.circle(WIN, s["color"], (int(s["x"]), int(s["y"])), s["size"])


# ---------------- MENU SCREEN ----------------
def menu_screen(stars):
    title_pulse = 0

    while True:
        dt = clock.tick(60)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    return PLAYING
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        update_and_draw_background(stars)

        # Animate glow
        title_pulse += dt * 0.005
        glow_alpha = (math.sin(title_pulse) + 1) / 2

        # Big glowing circle behind title
        glow_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(
            glow_surface,
            (0, 200, 255, int(120 * glow_alpha + 60)),
            (WIDTH // 2, HEIGHT // 3),
            160
        )
        WIN.blit(glow_surface, (0, 0))

        # Title text
        draw_text("BOOPIT", WIDTH // 2, HEIGHT // 3 - 15, (200, 240, 255))

        # Instructions moved lower so they don't overlap the orb
        draw_text("Move: WASD    Aim: Mouse    Shoot: Left Click",
                  WIDTH // 2, HEIGHT // 2 + 70)
        draw_text("Dash: Left Shift    Pause: ESC",
                  WIDTH // 2, HEIGHT // 2 + 105)

        draw_text("Press SPACE to Begin", WIDTH // 2, HEIGHT // 2 + 180, (255, 255, 255))
        draw_text("Press ESC to Quit", WIDTH // 2, HEIGHT // 2 + 220, (190, 190, 210))

        pygame.display.flip()


# ---------------- END SCREEN ----------------
def end_screen(stars, won):
    while True:
        dt = clock.tick(60)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r:
                    return PLAYING
                if e.key == pygame.K_m:
                    return MENU
                if e.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        update_and_draw_background(stars)

        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        WIN.blit(overlay, (0, 0))

        msg = "MISSION SUCCESS" if won else "MISSION FAILED"
        color = (0, 200, 255) if won else (255, 80, 110)
        draw_text(msg, WIDTH // 2, HEIGHT // 3, color)

        draw_text("Press R to Retry", WIDTH // 2, HEIGHT // 2, (220, 230, 255))
        draw_text("Press M for Main Menu", WIDTH // 2, HEIGHT // 2 + 40, (200, 210, 240))
        draw_text("Press ESC to Quit", WIDTH // 2, HEIGHT // 2 + 80, (180, 190, 220))

        pygame.display.flip()


# ---------------- GAMEPLAY ----------------
def play_game(stars):
    screen_shake = 0

    # power-ups
    speed_active = False
    speed_end_time = 0
    last_power_spawn = pygame.time.get_ticks()

    # dash
    last_dash = -99999
    last_direction = (1, 0)

    # player
    player = pygame.Rect(WIDTH // 2, HEIGHT // 2, PLAYER_SIZE, PLAYER_SIZE)

    bullets = []   # {"x","y","dx","dy","radius"}
    enemies = []   # {"x","y"}
    particles = [] # {"x","y","vx","vy","radius","color"}
    powerups = []  # {"x","y","type"}

    last_spawn = pygame.time.get_ticks()

    SURVIVE_TIME = 20.0
    elapsed_time = 0.0

    paused = False
    running = True
    won = False

    while running:
        dt = clock.tick(60)
        now = pygame.time.get_ticks()
        mouse = pygame.mouse.get_pos()

        # ---------- EVENTS ----------
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    # toggle pause
                    paused = not paused

                # dash
                if e.key == pygame.K_LSHIFT and not paused:
                    time_since_dash = now - last_dash
                    if time_since_dash >= DASH_COOLDOWN:
                        dir_x, dir_y = last_direction
                        if dir_x == 0 and dir_y == 0:
                            # if no movement, dash toward mouse
                            px, py = player.center
                            dx = mouse[0] - px
                            dy = mouse[1] - py
                            length = math.hypot(dx, dy)
                            if length != 0:
                                dir_x, dir_y = dx / length, dy / length
                        if dir_x != 0 or dir_y != 0:
                            player.x += int(dir_x * DASH_DISTANCE)
                            player.y += int(dir_y * DASH_DISTANCE)

                            # clamp inside screen
                            player.x = max(0, min(WIDTH - PLAYER_SIZE, player.x))
                            player.y = max(0, min(HEIGHT - PLAYER_SIZE, player.y))

                            last_dash = now
                            screen_shake = 8

                            # big dash particle burst
                            px, py = player.center
                            for _ in range(40):
                                ang = random.uniform(0, math.tau)
                                spd = random.uniform(3, 8)
                                particles.append({
                                    "x": px,
                                    "y": py,
                                    "vx": math.cos(ang) * spd,
                                    "vy": math.sin(ang) * spd,
                                    "radius": random.randint(3, 6),
                                    "color": (180, 240, 255),
                                })

                            # trailing streak along dash direction
                            for i in range(12):
                                trail_x = px - dir_x * i * 10
                                trail_y = py - dir_y * i * 10
                                particles.append({
                                    "x": trail_x,
                                    "y": trail_y,
                                    "vx": 0,
                                    "vy": 0,
                                    "radius": max(1, 10 - i * 0.8),
                                    "color": (120, 200, 255),
                                })

                # while paused, allow going back to menu or quitting
                if paused:
                    if e.key == pygame.K_m:
                        return MENU, False
                    if e.key == pygame.K_q:
                        pygame.quit()
                        sys.exit()

            # shooting
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and not paused:
                px, py = player.center
                mx, my = mouse
                dx = mx - px
                dy = my - py
                length = math.hypot(dx, dy)
                if length == 0:
                    length = 1
                dir_x = dx / length
                dir_y = dy / length
                bullets.append({
                    "x": px,
                    "y": py,
                    "dx": dir_x * BULLET_SPEED,
                    "dy": dir_y * BULLET_SPEED,
                    "radius": BULLET_SIZE,
                })
                # muzzle flash particles
                for _ in range(6):
                    particles.append({
                        "x": px,
                        "y": py,
                        "vx": random.uniform(-2, 2),
                        "vy": random.uniform(-2, 2),
                        "radius": random.randint(3, 5),
                        "color": (200, 240, 255),
                    })

        # ---------- UPDATE (NOT PAUSED) ----------
        if not paused:
            elapsed_time += dt / 1000.0

            # movement
            keys = pygame.key.get_pressed()
            move_x = 0
            move_y = 0
            if keys[pygame.K_w]:
                move_y -= 1
            if keys[pygame.K_s]:
                move_y += 1
            if keys[pygame.K_a]:
                move_x -= 1
            if keys[pygame.K_d]:
                move_x += 1

            if move_x != 0 or move_y != 0:
                length = math.hypot(move_x, move_y)
                dir_x = move_x / length
                dir_y = move_y / length
                last_direction = (dir_x, dir_y)
                speed = PLAYER_BASE_SPEED * (1.6 if speed_active else 1.0)
                player.x += int(dir_x * speed)
                player.y += int(dir_y * speed)

            # clamp
            player.x = max(0, min(WIDTH - PLAYER_SIZE, player.x))
            player.y = max(0, min(HEIGHT - PLAYER_SIZE, player.y))

            # spawn powerups
            if now - last_power_spawn > POWERUP_SPAWN_RATE:
                px = random.randint(60, WIDTH - 60)
                py = random.randint(60, HEIGHT - 60)
                p_type = random.choice(POWERUP_TYPES)
                powerups.append({"x": px, "y": py, "type": p_type})
                last_power_spawn = now

            # pickup powerups
            for p in powerups[:]:
                rect = pygame.Rect(
                    p["x"] - POWERUP_SIZE // 2,
                    p["y"] - POWERUP_SIZE // 2,
                    POWERUP_SIZE, POWERUP_SIZE
                )
                if rect.colliderect(player):
                    if p["type"] == "speed":
                        speed_active = True
                        speed_end_time = now + POWERUP_DURATION
                    powerups.remove(p)

            # powerup timeout
            if speed_active and now > speed_end_time:
                speed_active = False

            # spawn enemies
            if now - last_spawn > SPAWN_RATE:
                side = random.choice(["top", "bottom", "left", "right"])
                if side == "top":
                    enemies.append({"x": random.randint(0, WIDTH), "y": -40})
                elif side == "bottom":
                    enemies.append({"x": random.randint(0, WIDTH), "y": HEIGHT + 40})
                elif side == "left":
                    enemies.append({"x": -40, "y": random.randint(0, HEIGHT)})
                else:
                    enemies.append({"x": WIDTH + 40, "y": random.randint(0, HEIGHT)})
                last_spawn = now

            # update enemies toward player
            px, py = player.center
            for en in enemies:
                ang = math.atan2(py - en["y"], px - en["x"])
                en["x"] += math.cos(ang) * ENEMY_SPEED
                en["y"] += math.sin(ang) * ENEMY_SPEED

            # update bullets
            for b in bullets:
                b["x"] += b["dx"]
                b["y"] += b["dy"]

            # remove off-screen bullets
            bullets = [
                b for b in bullets
                if 0 <= b["x"] <= WIDTH and 0 <= b["y"] <= HEIGHT
            ]

            # particles
            for p in particles[:]:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["radius"] -= 0.15
                if p["radius"] <= 0:
                    particles.remove(p)

            # collisions: enemies vs player and bullets
            for en in enemies[:]:
                ex, ey = en["x"], en["y"]
                enemy_rect = pygame.Rect(
                    ex - ENEMY_SIZE // 2,
                    ey - ENEMY_SIZE // 2,
                    ENEMY_SIZE, ENEMY_SIZE
                )

                # enemy hits player
                if enemy_rect.colliderect(player):
                    running = False
                    won = False
                    break

                # enemy vs bullets
                hit = False
                for b in bullets[:]:
                    if enemy_rect.collidepoint(b["x"], b["y"]):
                        hit = True
                        bullets.remove(b)
                        break
                if hit:
                    enemies.remove(en)
                    screen_shake = 8
                    # explosion particles
                    for _ in range(18):
                        ang = random.uniform(0, math.tau)
                        spd = random.uniform(1, 4)
                        particles.append({
                            "x": ex,
                            "y": ey,
                            "vx": math.cos(ang) * spd,
                            "vy": math.sin(ang) * spd,
                            "radius": random.randint(3, 7),
                            "color": (255, 200, 220),
                        })

            # win condition
            if running and elapsed_time >= SURVIVE_TIME:
                running = False
                won = True

        # ---------- DRAW ----------
        update_and_draw_background(stars)

        # screen shake offsets
        if screen_shake > 0:
            shake_x = random.randint(-screen_shake, screen_shake)
            shake_y = random.randint(-screen_shake, screen_shake)
            screen_shake = max(0, screen_shake - 1)
        else:
            shake_x = shake_y = 0

        # powerups
        for p in powerups:
            pygame.draw.circle(
                WIN, POWER_SPEED_COLOR,
                (int(p["x"] + shake_x), int(p["y"] + shake_y)),
                POWERUP_SIZE // 2
            )

        # bullets
        for b in bullets:
            pygame.draw.circle(
                WIN, BULLET_COLOR,
                (int(b["x"] + shake_x), int(b["y"] + shake_y)),
                int(b["radius"])
            )

        # enemies
        for en in enemies:
            ex, ey = en["x"] + shake_x, en["y"] + shake_y
            pygame.draw.circle(WIN, ENEMY_GLOW, (int(ex), int(ey)), ENEMY_SIZE)
            pygame.draw.circle(WIN, ENEMY_CORE, (int(ex), int(ey)), ENEMY_SIZE // 2)

        # particles
        for p in particles:
            pygame.draw.circle(
                WIN, p["color"],
                (int(p["x"] + shake_x), int(p["y"] + shake_y)),
                int(max(1, p["radius"]))
            )

        # player
        px, py = player.center
        pygame.draw.circle(
            WIN, PLAYER_GLOW,
            (int(px + shake_x), int(py + shake_y)),
            PLAYER_SIZE + 12
        )
        pygame.draw.circle(
            WIN, PLAYER_CORE,
            (int(px + shake_x), int(py + shake_y)),
            PLAYER_SIZE // 2
        )

        # gun
        angle_deg = angle_to(mouse, player.center)
        angle_rad = math.radians(angle_deg)
        p1 = (px + shake_x, py + shake_y)
        p2 = (p1[0] + math.cos(angle_rad) * 40,
              p1[1] + math.sin(angle_rad) * 40)
        p3 = (p1[0] + math.cos(angle_rad + 0.4) * 22,
              p1[1] + math.sin(angle_rad + 0.4) * 22)
        pygame.draw.polygon(WIN, BULLET_COLOR, [p1, p2, p3])

        # HUD
        remaining = max(0, int(SURVIVE_TIME - elapsed_time))
        draw_text(f"Time Left: {remaining}", WIDTH // 2, 40)

        if speed_active:
            draw_text("SPEED BOOST ACTIVE", WIDTH // 2, 80, POWER_SPEED_COLOR)

        # dash cooldown indicator
        if last_dash < 0:
            dash_ready = True
        else:
            dash_ready = (now - last_dash) >= DASH_COOLDOWN
        if dash_ready:
            dash_text = "DASH READY"
        else:
            cd = max(0.0, (DASH_COOLDOWN - (now - last_dash)) / 1000.0)
            dash_text = f"DASH CD: {cd:.1f}s"
        draw_text(dash_text, WIDTH // 2, HEIGHT - 40, (200, 230, 255))

        # pause overlay + pause options
        if paused:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            WIN.blit(overlay, (0, 0))
            draw_text("PAUSED", WIDTH // 2, HEIGHT // 2 - 40, (220, 230, 255))
            draw_text("ESC: Resume    M: Main Menu    Q: Quit",
                      WIDTH // 2, HEIGHT // 2 + 10, (200, 210, 230))

        pygame.display.flip()

        # leave loop if finished
        if not running and not paused:
            break

    # return to main loop
    return END, won


# ---------------- MAIN LOOP ----------------
def main():
    stars = init_stars()
    state = MENU
    won = False

    while True:
        if state == MENU:
            state = menu_screen(stars)
        elif state == PLAYING:
            state, won = play_game(stars)
        elif state == END:
            state = end_screen(stars, won)


if __name__ == "__main__":
    main()

