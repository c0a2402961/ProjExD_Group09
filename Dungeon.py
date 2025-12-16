import os
import sys
import random
import math
import pygame as pg

WIDTH = 1100
HEIGHT = 650
FPS = 60
DEBUG_DRAW_GROUND_LINE = True

os.chdir(os.path.dirname(os.path.abspath(__file__)))
STAGE2_TMR = 1500 
GROUND_Y = HEIGHT - 60

# =========================
# クラス外関数
# =========================
def load_image(filename: str) -> pg.Surface:
    candidates = [os.path.join("fig", filename), filename]
    last_err = None
    for path in candidates:
        try:
            return pg.image.load(path).convert_alpha()
        except Exception as e:
            last_err = e
    # 指定画像がない場合の代用（デバッグ用）
    surf = pg.Surface((50, 50))
    surf.fill((255, 0, 255))
    return surf

def get_ground_y() -> int:
    return GROUND_Y

def set_ground_y(v: int) -> None:
    global GROUND_Y
    GROUND_Y = v

def stage_params(stage: int) -> dict:
    if stage == 1:
        return {"bg_file": "bg_1.jpg", "bg_speed": 4, "enemy_speed": 7, "spawn_interval": 60}
    return {"bg_file": "bg_2.jpg", "bg_speed": 6, "enemy_speed": 9, "spawn_interval": 45}

def detect_ground_y(bg_scaled: pg.Surface) -> int:
    w, h = bg_scaled.get_size()
    y_start, y_end = int(h * 0.40), int(h * 0.90)
    best_y = int(h * 0.75)
    best_score = 10**18
    for y in range(y_start, y_end):
        r, g, b, a = bg_scaled.get_at((w//2, y))
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        if lum < best_score:
            best_score = lum
            best_y = y
    return min(h - 1, best_y + 1)

# =========================
# クラス（中ボス関連）
# =========================

class Beam(pg.sprite.Sprite):
    """中ボスが放つビーム"""
    def __init__(self, pos: tuple[int, int]):
        super().__init__()
        raw_image = load_image("Beam.png")
        self.image = pg.transform.smoothscale(raw_image, (200, 80))
        self.rect = self.image.get_rect(center=pos)
        self._speed = 15

    def update(self):
        self.rect.x -= self._speed
        if self.rect.right < 0:
            self.kill()

    def get_rect(self) -> pg.Rect:
        return self.rect


class Meteor(pg.sprite.Sprite):
    """中ボスが降らせる隕石"""
    def __init__(self, target_x: int):
        super().__init__()
        size = random.randint(50, 150)
        raw_image = load_image("Meteor.png")
        self.image = pg.transform.smoothscale(raw_image, (size, size))
        self.rect = self.image.get_rect(center=(target_x, -50))
        self._speed_y = 6

    def update(self):
        self.rect.y += self._speed_y
        if self.rect.top > HEIGHT:
            self.kill()

    def get_rect(self) -> pg.Rect:
        return self.rect


class MidBoss(pg.sprite.Sprite):
    """
    中ボス：画面右側に滞在し、ビームと隕石で攻撃
    """
    def __init__(self):
        super().__init__()
        raw_image = load_image("Ramieru.png")
        self.image = pg.transform.smoothscale(raw_image, (300, 300))
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH - 150, get_ground_y() - 200)
        
        self._timer = 0
        self._hp = 100 # 追加機能と連携可能

    def update(self, bird_rect: pg.Rect, beams: pg.sprite.Group, meteors: pg.sprite.Group):
        self._timer += 1

        # 【上下移動の計算】
        # math.sin を使うことで滑らかな波のような動きにする
        # 0.05 を変えると速さが、100 を変えると揺れ幅が変わる
        move_y = math.sin(self._timer * 0.05) * 100

        # 基準点（地面の高さ）を更新しつつ、計算した揺れを加算する
        self._base_y = get_ground_y() - 250
        self.rect.centery = self._base_y + move_y

        # ビーム発射（1.5秒に1回）
        if self._timer % 90 == 0:
            beams.add(Beam(self.rect.center))

        # 隕石落下（2秒に1回、こうかとんの頭上に降らす）
        if self._timer % 120 == 0:
            meteors.add(Meteor(bird_rect.centerx))

    def get_rect(self) -> pg.Rect:
        return self.rect

    def get_hp(self) -> int:
        return self._hp

# =========================
# 既存クラス
# =========================

class Background:
    def __init__(self, bg_file: str, speed: int):
        raw = load_image(bg_file)
        self._img = pg.transform.smoothscale(raw, (WIDTH, HEIGHT))
        self._speed = speed
        self._x1, self._x2 = 0, WIDTH
        set_ground_y(detect_ground_y(self._img))

    def update(self, screen: pg.Surface):
        self._x1 -= self._speed
        self._x2 -= self._speed
        if self._x1 <= -WIDTH: self._x1 = self._x2 + WIDTH
        if self._x2 <= -WIDTH: self._x2 = self._x1 + WIDTH
        screen.blit(self._img, (self._x1, 0))
        screen.blit(self._img, (self._x2, 0))

    def get_speed(self) -> int:
        return self._speed


class Bird(pg.sprite.Sprite):
    def __init__(self, num: int, xy: tuple[int, int]):
        super().__init__()
        img0 = pg.transform.rotozoom(load_image(f"{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)
        self._imgs = {+1: img, -1: img0}
        self._dir = +1
        self.image = self._imgs[self._dir]
        self.rect = self.image.get_rect(center=xy)
        self.rect.bottom = get_ground_y()
        self._vx, self._vy = 0, 0.0
        self._speed, self._gravity = 8, 0.85
        self._jump_v0, self._jump_count, self._max_jump = -15, 0, 2
        self._damage_tmr = 0  # 追加：ダメージ点滅用タイマー

    def set_damage(self):
            #"""追加：ダメージを受けたときにタイマーをセットする"""
            self._damage_tmr = 30  # 30フレーム（約0.5秒）点滅させる

    def try_jump(self):
        if self._jump_count < self._max_jump:
            self._vy = self._jump_v0
            self._jump_count += 1

    def update(self, key_lst: list[bool], screen: pg.Surface):
        self._vx = 0
        if key_lst[pg.K_LEFT]: self._vx, self._dir = -self._speed, -1
        if key_lst[pg.K_RIGHT]: self._vx, self._dir = +self._speed, +1
        self.rect.x += self._vx
        self.rect.left = max(0, min(WIDTH - self.rect.width, self.rect.left))
        
        self._vy += self._gravity
        self.rect.y += int(self._vy)
        gy = get_ground_y()
        if self.rect.bottom >= gy:
            self.rect.bottom, self._vy, self._jump_count = gy, 0.0, 0

        # 追加：ダメージ点滅ロジック
        if self._damage_tmr > 0:
            self._damage_tmr -= 1
            # 2フレームに1回描画しない時間を作ることで点滅させる
            if self._damage_tmr % 4 < 2:
                return # 描画せずに終了（点滅の「消える」瞬間）

        self.image = self._imgs[self._dir]
        screen.blit(self.image, self.rect)

    def get_rect(self) -> pg.Rect:
        return self.rect


class Enemy(pg.sprite.Sprite):
    def __init__(self, stage: int):
        super().__init__()
        self._speed = stage_params(stage)["enemy_speed"]
        self.image = pg.Surface((50, 50), pg.SRCALPHA)
        pg.draw.rect(self.image, (230, 70, 70), (0, 0, 50, 50))
        self.rect = self.image.get_rect(left=WIDTH + 100, bottom=get_ground_y())

    def update(self):
        self.rect.x -= self._speed
        self.rect.bottom = get_ground_y()
        if self.rect.right < 0: self.kill()

    def get_rect(self) -> pg.Rect:
        return self.rect


# =========================
# メイン
# =========================
def main():
    pg.display.set_caption("こうかとん横スクロール（中ボス追加）")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    clock = pg.time.Clock()

    stage = 1
    params = stage_params(stage)
    bg = Background(params["bg_file"], params["bg_speed"])
    bird = Bird(3, (200, get_ground_y()))
    
    enemies = pg.sprite.Group()
    boss_group = pg.sprite.Group()
    beams = pg.sprite.Group()
    meteors = pg.sprite.Group()

    tmr = 0
    score = 0 # 担当の人と連携想定
    mid_boss_spawned = False

    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT: return
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE: return
                if event.key == pg.K_UP: bird.try_jump()

        # ステージ遷移
        if stage == 1 and tmr >= STAGE2_TMR:
            stage = 2
            params = stage_params(stage)
            bg = Background(params["bg_file"], params["bg_speed"])
            bird.get_rect().bottom = get_ground_y()

        # スコア加算（生存時間で増加と仮定）
        if not mid_boss_spawned:
            score += 1
            if score > 500: # 500フレーム生存で中ボス出現
                mid_boss_spawned = True
                boss_group.add(MidBoss())

        # 敵生成（中ボスがいない間だけモブが出る）
        if not mid_boss_spawned and tmr % params["spawn_interval"] == 0:
            enemies.add(Enemy(stage))

        # 更新
        bg.update(screen)
        if DEBUG_DRAW_GROUND_LINE:
            pg.draw.line(screen, (0, 0, 0), (0, get_ground_y()), (WIDTH, get_ground_y()), 2)

        bird.update(key_lst, screen)
        enemies.update()
        enemies.draw(screen)
        
        # 【中ボスの更新・描画エリア】
        if mid_boss_spawned:
            # プレイヤーの位置（bird.get_rect()）を渡して、狙いを定めさせる
            boss_group.update(bird.get_rect(), beams, meteors)
            
            # ビームと隕石も一緒に更新
            beams.update()
            meteors.update()
            
            # まとめて描画
            boss_group.draw(screen)
            beams.draw(screen)
            meteors.draw(screen)

            # ビームとの衝突判定（当たったらビームを消す）
        if pg.sprite.spritecollide(bird, beams, True):
            print("ビームがヒット！")  # ログ出力(仮)
            bird.set_damage()  # 追加：点滅開始


        # 隕石との衝突判定（当たったら隕石を消す）
        if pg.sprite.spritecollide(bird, meteors, True):
            print("隕石がヒット！")  # ログ出力(仮)
            bird.set_damage()  # 追加：点滅開始
        
        pg.display.update()
        tmr += 1
        clock.tick(FPS)

if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
