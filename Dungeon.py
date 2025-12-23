import os
import sys
import random
import math
import pygame as pg
import math

WIDTH = 1100
HEIGHT = 650
FPS = 60

DEBUG_DRAW_GROUND_LINE = True

os.chdir(os.path.dirname(os.path.abspath(__file__)))

STAGE2_TMR = 1500
BOSS_TMR = 1200

GROUND_Y = HEIGHT - 60
# ===== HP/ダメージ（追加）=====
HP_MAX = 100
DMG = 20
POPUP_FRAMES = 120   # 約2秒（60FPS想定）
INV_FRAMES = 30      # 無敵0.5秒（接触中に毎フレーム減るのを防ぐための実装上の仮定）
# =====================
# ゲーム状態
# =====================
STATE_START = 0
STATE_PLAY = 1
STATE_TO_FINAL = 2
STATE_CLEAR = 3
STATE_GAMEOVER = 4
# ===== 右下UI（Attack/Status）（追加）=====
BOX_W, BOX_H = 220, 110
BOX_GAP = 14
BOX_MARGIN = 20
# ★ 足元補正値
FOOT_OFFSET_BIRD = 10
FOOT_OFFSET_ENEMY = 5
FOOT_OFFSET_BOSS = 8


# =========================
# 共通関数
# =========================
def load_font(size):
    return pg.font.SysFont("meiryo", size)
def load_image(filename: str) -> pg.Surface:
    """
    画像読み込み（fig/filename -> filename の順に探す）
    ※displayが未生成のタイミングでも落ちないようにする
    """
    candidates = [os.path.join("fig", filename), filename]
    for path in candidates:
        try:
            img = pg.image.load(path)
            # 画面が作られている時だけ convert_alpha する
            if pg.display.get_init() and pg.display.get_surface() is not None:
                img = img.convert_alpha()
            return img
        except:
            pass
    raise SystemExit(f"画像 {filename} の読み込みに失敗しました")
# =====================
# 画面描画
# =====================

def draw_start_screen(screen):
    screen.fill((0, 0, 0))

    font = load_font(80)
    title = font.render("こうかとんダンジョン", True, (255,255,255))
    title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 80))
    screen.blit(title, title_rect)

    font2 = load_font(40)
    start = font2.render("ENTERでスタート", True, (200,200,200))
    start_rect = start.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40))
    screen.blit(start, start_rect)


def draw_to_final_screen(screen):
    screen.fill((0, 0, 0))
    font = load_font(80)
    text = font.render("最終ステージへ", True, (255,255,0))
    rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text, rect)


def draw_clear_screen(screen):
    screen.fill((0, 0, 0))
    font = load_font(80)
    text = font.render("クリア", True, (0,255,0))
    rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text, rect)


def draw_gameover_screen(screen):
    screen.fill((0, 0, 0))
    font = load_font(80)
    text = font.render("GAME OVER", True, (255,0,0))
    rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text, rect)


#仮設定
def draw_hp(screen, hp):
    font =load_font(36)
    screen.blit(font.render(f"HP: {hp}", True, (255,255,255)), (20, 20))



def clamp_in_screen(rect: pg.Rect) -> pg.Rect:
    rect.left = max(0, rect.left)
    rect.right = min(WIDTH, rect.right)
    rect.top = max(0, rect.top)
    rect.bottom = min(HEIGHT, rect.bottom)
    return rect


def get_ground_y() -> int:
    return GROUND_Y

def set_ground_y(v: int) -> None:
    global GROUND_Y
    GROUND_Y = v


def stage_params(stage: int) -> dict[str, int | str]:
    """
    ステージごとの設定

     Returns:
        dict[str, int | str]:
            "bg_file" (str): 背景画像ファイル名
            "bg_speed" (int): 背景スクロール速度
            "enemy_speed" (int): 敵の移動速度
            "item_speed" (int): アイテムの移動速度
            "spawn_interval" (int): 敵の生成間隔（フレーム）
    
    """
    if stage == 1:
        return {
            "bg_file": "bg_1.jpg",
            "bg_speed": 4,
            "enemy_speed": 5,
            "item_speed": 5,
            "spawn_interval": 60,  # フレーム間隔
        }
    return {
        "bg_file": "bg_2.jpg",
        "bg_speed": 6,
        "enemy_speed": 5,
        "item_speed": 7,
        "spawn_interval": 45,
    }


def should_switch_stage(tmr: int) -> bool:
    return tmr >= STAGE2_TMR

#高柳変更
def spawn_enemy(enemies: pg.sprite.Group, stage: int) -> None:
    params = stage_params(stage)
    kind = random.choice(["ground", "air"])  # 地面敵 / 空中敵
    enemies.add(Enemy(stage=stage, kind=kind, speed=params["enemy_speed"]))




def detect_ground_y(bg_scaled: pg.Surface) -> int:
    """
    リサイズ済み背景から「暗くて横方向に均一な水平ライン」を推定し、
    その“1px下”を地面Yとして返す。
    """
    w, h = bg_scaled.get_size()

    y_start = int(h * 0.40)
    y_end = int(h * 0.90)

    x_step = 4
    best_y = int(h * 0.75)
    best_score = 10**18
    for y in range(y_start, y_end):
        s = 0.0
        s2 = 0.0
        n = 0
        for x in range(0, w, x_step):
            r, g, b, a = bg_scaled.get_at((x, y))
            lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
            s += lum
            s2 += lum * lum
            n += 1
        mean = s / n
        var = (s2 / n) - mean * mean
        std = (var ** 0.5) if var > 0 else 0.0

        score = mean + 0.3 * std
        if score < best_score:
            best_score = score
            best_y = y

    return min(h - 1, best_y + 1)

# =========================
# クラス
# =========================

class Beam_tbos(pg.sprite.Sprite):
    """中ボスが放つビーム"""
    def __init__(self, pos: tuple[int, int]):
        super().__init__()
        raw_image = load_image("Beam_tbos.png")
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
        self.hp = 500
        self._hp = 100 # 追加機能と連携可能

    def update(self, bird_rect: pg.Rect, beams_tbos: pg.sprite.Group, meteors: pg.sprite.Group):
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
            beams_tbos.add(Beam_tbos(self.rect.center))

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
        self._x1 = 0
        self._x2 = WIDTH
        set_ground_y(detect_ground_y(self._img))

    def update(self, screen):
        self._x1 -= self._speed
        self._x2 -= self._speed
        if self._x1 <= -WIDTH: self._x1 = self._x2 + WIDTH
        if self._x2 <= -WIDTH: self._x2 = self._x1 + WIDTH
        screen.blit(self._img, (self._x1, 0))
        screen.blit(self._img, (self._x2, 0))

    def get_speed(self) -> int:
        return self._speed


class Bird(pg.sprite.Sprite):
    """
    プレイヤー：左右移動＋ジャンプ＋二段ジャンプ
    """
    def __init__(self, num: int, xy: tuple[int, int]):
        super().__init__()
        img0 = pg.transform.rotozoom(load_image(f"{num}.png"), 0, 0.9)
        img = pg.transform.flip(img0, True, False)
        self._imgs = {+1: img, -1: img0}
        self._dir = +1

        self.image = self._imgs[self._dir]
        self.rect = self.image.get_rect()

        # 物理（ここは一切変更しない）
        self._vx = 0
        self._vy = 0
        self._speed = 8
        self._gravity = 0.85
        self._jump_v0 = -15
        self._jump_count = 0
        self._max_jump = 2

        self.rect.center = xy
        self.rect.bottom = get_ground_y() + FOOT_OFFSET_BIRD

        # --- HP/無敵時間（追加） ---高柳
        self.hp = 100
        self._inv = 0   # 無敵フレーム（連続ダメ防止）

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

    def update(self, key_lst: list[bool], screen: pg.Surface) -> None:
        self._vx = 0
        if key_lst[pg.K_LEFT]:
            self._vx = -self._speed
            self._dir = -1
        if key_lst[pg.K_RIGHT]:
            self._vx = +self._speed*0.5
            self._dir = +1
        if self._inv > 0:
            self._inv -= 1


        self.rect.x += self._vx
        self.rect = clamp_in_screen(self.rect)

        self._vy += self._gravity
        self.rect.y += int(self._vy)

        gy = get_ground_y()
        if self.rect.bottom >= gy:
            self.rect.bottom = gy
            self._vy = 0.0
            self._jump_count = 0

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

    def set_max_jump(self, n: int) -> None:
        self._max_jump = max(1, int(n))

    def get_max_jump(self) -> int:
        return self._max_jump

    def get_speed(self) -> int:
        return self._speed
    
    #高柳追加
    def take_damage(self, dmg: int) -> None:
        """無敵中でなければダメージを受ける"""
        if self._inv == 0:
            self.hp = max(0, self.hp - dmg)
            self._inv = 30  # 0.5秒くらい（60FPS想定）

    def get_vy(self) -> float:
        return self._vy

    def set_vy(self, v: float) -> None:
        self._vy = v


#変更高柳
class Enemy(pg.sprite.Sprite):
    """
    モブ敵（2パターン）
    - ground : 地面に沿って左へ流れる（ジャンプで踏める）
    - air    : 空中を左へ流れる（踏める）
    ステージ1: doragon1.png / gimen1.png
    ステージ2: doragon2.png / gimen2.png
    """
    def __init__(self, stage: int, kind: str = "ground", speed: int = 7):
        super().__init__()
        self.stage = stage
        self.kind = kind

        # ステージごとの画像を選ぶ（UFO/alienは使わない）
        if self.stage == 1:
            img_file = "enemy3.png" if self.kind == "ground" else "dagon.png"
        else:
            img_file = "enemy4.png" if self.kind == "ground" else "stennow.png"

        base = load_image(img_file)

        # サイズ調整（必要なら数字だけ変えてOK）
        scale = 0.05 if self.kind == "ground" else 0.05
        self.image = pg.transform.rotozoom(base, 0, scale)
        self.rect = self.image.get_rect()

        # 右端から左へ流れる（地面と平行）
        self.vx = -speed
        self.vy = 0
        self.rect.left = WIDTH + random.randint(0, 80)

        gy = get_ground_y()
        if self.kind == "ground":
            self.rect.bottom = gy
        else:
            y = gy - random.randint(120, 260)
            self.rect.bottom = max(40, y)

    def update(self):
        self.rect.move_ip(self.vx, self.vy)

        if (
            self.rect.right < -50 or
            self.rect.left > WIDTH + 50 or
            self.rect.top > HEIGHT + 50
        ):
            self.kill()


class Boss(pg.sprite.Sprite):
    def __init__(self):
        super().__init__()

        self.base_image = pg.transform.smoothscale(
            load_image("zerueru1.png"), (200, 200)
        )
        self.hit_image = self.base_image.copy()
        self.hit_image.fill((255, 80, 80), special_flags=pg.BLEND_RGBA_MULT)

        self.image = self.base_image
        self.rect = self.image.get_rect()
        self.rect.centerx = WIDTH // 2
        self.rect.bottom = get_ground_y() + FOOT_OFFSET_BOSS

        self._vx = random.choice([-4, 4])
        self._vy = 0
        self._gravity = 0.8
        self._jump_v0 = -14

        self._action_tmr = 0
        self._next_action = random.randint(60, 120)

        self.hit_timer = 0

    def update(self):
        self._action_tmr += 1
        if self._action_tmr >= self._next_action:
            self._action_tmr = 0
            self._next_action = random.randint(60, 120)
            self._vx = random.choice([-4, 4])
            if random.random() < 0.4 and self.rect.bottom >= get_ground_y() + FOOT_OFFSET_BOSS:
                self._vy = self._jump_v0

        self.rect.x += self._vx
        if self.rect.left <= 80 or self.rect.right >= WIDTH - 80:
            self._vx *= -1

        self._vy += self._gravity
        self.rect.y += int(self._vy)

        if self.rect.bottom >= get_ground_y() + FOOT_OFFSET_BOSS:
            self.rect.bottom = get_ground_y() + FOOT_OFFSET_BOSS
            self._vy = 0

        if self.hit_timer > 0:
            self.hit_timer -= 1

        self.image = self.hit_image if self.hit_timer > 0 else self.base_image

    def on_hit(self):
        self.hit_timer = 10

    def draw(self, screen):
        screen.blit(self.image, self.rect)



    
class Explosion(pg.sprite.Sprite):
    """
    爆発エフェクト：中心で拡大縮小を繰り返しながら消滅
    """
    def __init__(self, center_xy: tuple[int, int], life: int = 30):
        super().__init__()
        img = load_image("explosion.gif")
        self._imgs = [img, pg.transform.flip(img, True, True)] # 拡大縮小用に2枚用意
        self.image = self._imgs[0]
        self.rect = self.image.get_rect(center=center_xy)
        self._life = life

    def update(self) -> None:
        self._life -= 1
        self.image = self._imgs[(self._life // 5) % 2] # 5フレームごとに切替
        if self._life <= 0:
            self.kill()

class Beam(pg.sprite.Sprite):
    """
    攻撃弾（ビーム）。

    仕様:
    - 発射位置から右方向へ直進
    - 画面外に出たら消滅
    """
    RANGE_PX = 200  # ビーム到達距離（発射位置からの相対）
    def __init__(self, start_xy: tuple[int, int]):
        super().__init__()
        self.image = load_image("beam_k.png")
        self.rect = self.image.get_rect(center=start_xy)
        self._vx = 16
        self._end_x = self.rect.centerx + self.RANGE_PX

    def update(self) -> None:
        self.rect.x += self._vx
        if self.rect.left >= self._end_x:
            self.kill()

class Arrow(pg.sprite.Sprite):
    """
    矢：放物線を描きつつ右へ進む
    """
    def __init__(self, start_xy: tuple[int, int]):
        super().__init__()
        self._base_image = load_image("arrow.png")  # 元画像を保持（回転はここから作る）
        self.image = self._base_image
        self.image = pg.transform.rotozoom(self._base_image, 0, 0.2)
        self.rect = self.image.get_rect(center=start_xy)

        self._vx = 16
        self._vy = -10.5
        self._g = 0.6

        self._angle = 0.0  # 現在角度（無駄な回転を減らす用）

    def update(self) -> None:
        """
        矢を更新する。
        - 右方向へ進みつつ重力で落下する
        - 上昇中(_vy<0)は右向き固定
        - 落下開始後(_vy>=0)は進行方向に合わせて右下向きに回転
        - 地面に触れた瞬間に消滅
        """
        # 位置更新
        self.rect.x += self._vx
        self._vy += self._g
        self.rect.y += int(self._vy)

        # --- 向き更新 ---
        # 発射直後（上昇中）は右向き固定、落ち始めたら進行方向に向ける
        if self._vy < 0:
            new_angle = 0.0
        else:
            # pygame座標はyが下に増えるので、角度は -atan2(vy, vx)
            new_angle = -math.degrees(math.atan2(self._vy, self._vx)) - 45

        # 角度が少し変わったときだけ回転（軽量化）
        if abs(new_angle - self._angle) > 1.0:
            self._angle = new_angle
            center = self.rect.center
            self.image = pg.transform.rotozoom(self._base_image, self._angle, 0.2)
            self.rect = self.image.get_rect(center=center)

        # 地面に触れた瞬間消滅
        if self.rect.bottom >= get_ground_y():
            self.kill()
        if self.rect.left > WIDTH:
            self.kill()


class ItemDef:
    """
    アイテムの“定義情報”を保持するクラス（スポーンや描画用）。

    Fields:
    - item_id: アイテム識別子（例: "Beam", "arrow", "kinoko", "tabaco"）
    - category: "attack" または "status"
    - img_file: 画像ファイル名
    - weight: 重み付き抽選で使う重み
    - scale: 描画倍率（Item生成時に適用）
    """
    def __init__(self, item_id: str, category: str, img_file: str, weight: int, scale: float = 1.0):
        self._item_id = item_id          # "Beam", "kinoko" など
        self._category = category        # "attack" or "status"
        self._img_file = img_file        # 画像ファイル名
        self._weight = weight
        self._scale = scale

    def get_item_id(self) -> str:
        return self._item_id

    def get_category(self) -> str:
        return self._category

    def get_img_file(self) -> str:
        return self._img_file
    
    def get_weight(self) -> int:
        return self._weight

    def get_scale(self) -> float:
        return self._scale

class Inventory:
    """
    プレイヤーの所持アイテム状態を管理する。

    仕様:
    - 攻撃アイテムは1つだけ保持（attackスロット）
    - 状態アイテムは1つだけ保持（statusスロット）
    - 同カテゴリで別 item_id を取得した場合は、後から取った方で置換する
    """
    def __init__(self, item_defs: dict[str, ItemDef]):
        self._defs = item_defs
        self._attack_id = None
        self._status_id = None

    def pickup_attack(self, item_id: str) -> None:
        self._attack_id = item_id

    def pickup_status_basic(self, item_id: str) -> None:
        self._status_id = item_id

    def clear_status(self) -> None:
        self._status_id = None

    def get_attack(self) -> str | None:
        return self._attack_id

    def get_status(self) -> str | None:
        return self._status_id
    
class Item(pg.sprite.Sprite):
    """
    画面右端から左へ流れるアイテム（取得対象）。

    - 画像は ItemDef に従って読み込む（scaleも適用）
    - 出現Xは右端外（WIDTH + 乱数）
    - 出現Yは「画面上限〜地面直上」の範囲でランダム
    - updateで左へ移動し、画面外に出たら消滅
    """
    def __init__(self, idef: ItemDef, stage: int):
        super().__init__()
        self._item_id = idef.get_item_id()
        self._category = idef.get_category()
        self._speed = stage_params(stage)["item_speed"]

        img = load_image(idef.get_img_file())
        if idef.get_scale() != 1.0:
            img = pg.transform.rotozoom(img, 0, idef.get_scale())
        self.image = img
        self.rect = self.image.get_rect()

        self.rect.left = WIDTH + random.randint(0, 200)

        # 地面より上のどこかに出す
        gy = get_ground_y()
        margin = 10
        lowest = gy - (self.rect.height // 2) - margin   # これより下に出さない
        highest = max(60,self.rect.height // 2 + margin)                                     # これより上に出さない（画面上部）

        if highest > lowest:
            self.rect.centery = (highest + lowest) // 2
        else:
            self.rect.centery = random.randint(highest, lowest)


    def update(self) -> None:
        self.rect.x -= self._speed
        if self.rect.right < 0:
            self.kill()

    def get_item_id(self) -> str:
        return self._item_id

    def get_category(self) -> str:
        return self._category
    

# スポーン間隔(フレーム) と スポーン確率
ITEM_SPAWN_INTERVAL_STAGE1 = 90   # 1.5秒(60FPS想定)
ITEM_SPAWN_INTERVAL_STAGE2 = 70
ITEM_SPAWN_PROB_STAGE1 = 0.55
ITEM_SPAWN_PROB_STAGE2 = 0.65


def pick_weighted_item_id(item_defs: dict[str, ItemDef], stage: int) -> str:
    """
    item_defs の weight に基づいて item_id を1つ返す（重み付き抽選）。

    Args:
        item_defs: item_id -> ItemDef の辞書
        stage: 現状は抽選ロジックに影響しないが、将来ステージ別抽選に拡張できるため引数として保持

    Returns:
        str: 抽選された item_id
    """
    ids = list(item_defs.keys())
    weights = [max(0, item_defs[i].get_weight()) for i in ids]
    total = sum(weights)
    if total <= 0:
        # 全部0なら先頭
        return ids[0]

    r = random.randint(1, total)
    acc = 0
    for i, w in zip(ids, weights):
        acc += w
        if r <= acc:
            return i
    return ids[-1]


def maybe_spawn_item(tmr: int, stage: int, item_defs: dict[str, ItemDef], items: pg.sprite.Group) -> None:
    """
    アイテムをスポーンするかを判定し、スポーンする場合は items に追加する。

    - stage に応じてスポーン間隔(interval)と確率(prob)を切り替える
    - tmr が interval の倍数のタイミングのみ抽選する
    - 当選したら重み付き抽選で item_id を選ぶ
    """
    if stage == 1:
        interval = ITEM_SPAWN_INTERVAL_STAGE1
        prob = ITEM_SPAWN_PROB_STAGE1
    else:
        interval = ITEM_SPAWN_INTERVAL_STAGE2
        prob = ITEM_SPAWN_PROB_STAGE2

    if tmr % interval != 0:
        return

    if random.random() > prob:
        return

    item_id = pick_weighted_item_id(item_defs, stage)
    items.add(Item(item_defs[item_id], stage))
    
def apply_status_pickup(item_id: str, inv: Inventory, bird: Bird) -> None:
    """
    状態アイテム取得時の特殊ルールを適用する。

    仕様:
    - tabaco：所持中は二段ジャンプ不可（max_jump=1）
    - kinoko：
        - 無状態で取得 -> max_jump=3（状態は kinoko）
        - tabaco所持中に取得 -> tabacoを打ち消し無状態へ（max_jump=2）

    副作用:
    - inv の状態スロット（status）を書き換える
    - bird の最大ジャンプ回数を変更する
    """
    cur_status = inv.get_status()

    if item_id == "tabaco":
        inv.pickup_status_basic("tabaco")
        bird.set_max_jump(1)
        return

    if item_id == "kinoko":
        if cur_status == "tabaco":
            # 打ち消し：無状態へ戻す
            inv.clear_status()
            bird.set_max_jump(2)
            return
        else:
            inv.pickup_status_basic("kinoko")
            bird.set_max_jump(3)
            return

    # 他の状態アイテムが増えたらここに追加
    inv.pickup_status_basic(item_id)

def apply_status_from_current(inv: Inventory, bird: Bird) -> None:
    """
    ステージ切替などで、現在の所持状態に合わせてジャンプ数を再適用したい場合用
    """
    st = inv.get_status()
    if st == "tabaco":
        bird.set_max_jump(1)
    elif st == "kinoko":
        bird.set_max_jump(3)
    else:
        bird.set_max_jump(2)



    
class Explosion(pg.sprite.Sprite):
    """
    爆発エフェクト：中心で拡大縮小を繰り返しながら消滅
    """
    def __init__(self, center_xy: tuple[int, int], life: int = 30):
        super().__init__()
        img = load_image("explosion.gif")
        self._imgs = [img, pg.transform.flip(img, True, True)] # 拡大縮小用に2枚用意
        self.image = self._imgs[0]
        self.rect = self.image.get_rect(center=center_xy)
        self._life = life

    def update(self) -> None:
        self._life -= 1
        self.image = self._imgs[(self._life // 5) % 2] # 5フレームごとに切替
        if self._life <= 0:
            self.kill()

class Beam(pg.sprite.Sprite):
    """
    攻撃弾（ビーム）。

    仕様:
    - 発射位置から右方向へ直進
    - 画面外に出たら消滅
    """
    RANGE_PX = 200  # ビーム到達距離（発射位置からの相対）
    def __init__(self, start_xy: tuple[int, int]):
        super().__init__()
        self.image = load_image("beam_k.png")
        self.rect = self.image.get_rect(center=start_xy)
        self._vx = 16
        self._end_x = self.rect.centerx + self.RANGE_PX

    def update(self) -> None:
        self.rect.x += self._vx
        if self.rect.left >= self._end_x:
            self.kill()

class Arrow(pg.sprite.Sprite):
    """
    矢：放物線を描きつつ右へ進む
    """
    def __init__(self, start_xy: tuple[int, int]):
        super().__init__()
        self._base_image = load_image("arrow.png")  # 元画像を保持（回転はここから作る）
        self.image = self._base_image
        self.image = pg.transform.rotozoom(self._base_image, 0, 0.2)
        self.rect = self.image.get_rect(center=start_xy)

        self._vx = 16
        self._vy = -10.5
        self._g = 0.6

        self._angle = 0.0  # 現在角度（無駄な回転を減らす用）

    def update(self) -> None:
        """
        矢を更新する。
        - 右方向へ進みつつ重力で落下する
        - 上昇中(_vy<0)は右向き固定
        - 落下開始後(_vy>=0)は進行方向に合わせて右下向きに回転
        - 地面に触れた瞬間に消滅
        """
        # 位置更新
        self.rect.x += self._vx
        self._vy += self._g
        self.rect.y += int(self._vy)

        # --- 向き更新 ---
        # 発射直後（上昇中）は右向き固定、落ち始めたら進行方向に向ける
        if self._vy < 0:
            new_angle = 0.0
        else:
            # pygame座標はyが下に増えるので、角度は -atan2(vy, vx)
            new_angle = -math.degrees(math.atan2(self._vy, self._vx)) - 45

        # 角度が少し変わったときだけ回転（軽量化）
        if abs(new_angle - self._angle) > 1.0:
            self._angle = new_angle
            center = self.rect.center
            self.image = pg.transform.rotozoom(self._base_image, self._angle, 0.2)
            self.rect = self.image.get_rect(center=center)

        # 地面に触れた瞬間消滅
        if self.rect.bottom >= get_ground_y():
            self.kill()
        if self.rect.left > WIDTH:
            self.kill()


class ItemDef:
    """
    アイテムの“定義情報”を保持するクラス（スポーンや描画用）。

    Fields:
    - item_id: アイテム識別子（例: "Beam", "arrow", "kinoko", "tabaco"）
    - category: "attack" または "status"
    - img_file: 画像ファイル名
    - weight: 重み付き抽選で使う重み
    - scale: 描画倍率（Item生成時に適用）
    """
    def __init__(self, item_id: str, category: str, img_file: str, weight: int, scale: float = 1.0):
        self._item_id = item_id          # "Beam", "kinoko" など
        self._category = category        # "attack" or "status"
        self._img_file = img_file        # 画像ファイル名
        self._weight = weight
        self._scale = scale

    def get_item_id(self) -> str:
        return self._item_id

    def get_category(self) -> str:
        return self._category

    def get_img_file(self) -> str:
        return self._img_file
    
    def get_weight(self) -> int:
        return self._weight

    def get_scale(self) -> float:
        return self._scale

class Inventory:
    """
    プレイヤーの所持アイテム状態を管理する。

    仕様:
    - 攻撃アイテムは1つだけ保持（attackスロット）
    - 状態アイテムは1つだけ保持（statusスロット）
    - 同カテゴリで別 item_id を取得した場合は、後から取った方で置換する
    """
    def __init__(self, item_defs: dict[str, ItemDef]):
        self._defs = item_defs
        self._attack_id = None
        self._status_id = None

    def pickup_attack(self, item_id: str) -> None:
        self._attack_id = item_id

    def pickup_status_basic(self, item_id: str) -> None:
        self._status_id = item_id

    def clear_status(self) -> None:
        self._status_id = None

    def get_attack(self) -> str | None:
        return self._attack_id

    def get_status(self) -> str | None:
        return self._status_id
    
class Item(pg.sprite.Sprite):
    """
    画面右端から左へ流れるアイテム（取得対象）。

    - 画像は ItemDef に従って読み込む（scaleも適用）
    - 出現Xは右端外（WIDTH + 乱数）
    - 出現Yは「画面上限〜地面直上」の範囲でランダム
    - updateで左へ移動し、画面外に出たら消滅
    """
    def __init__(self, idef: ItemDef, stage: int):
        super().__init__()
        self._item_id = idef.get_item_id()
        self._category = idef.get_category()
        self._speed = stage_params(stage)["item_speed"]

        img = load_image(idef.get_img_file())
        if idef.get_scale() != 1.0:
            img = pg.transform.rotozoom(img, 0, idef.get_scale())
        self.image = img
        self.rect = self.image.get_rect()

        self.rect.left = WIDTH + random.randint(0, 200)

        # 地面より上のどこかに出す
        gy = get_ground_y()
        margin = 10
        lowest = gy - (self.rect.height // 2) - margin   # これより下に出さない
        highest = max(60,self.rect.height // 2 + margin)                                     # これより上に出さない（画面上部）

        if highest > lowest:
            self.rect.centery = (highest + lowest) // 2
        else:
            self.rect.centery = random.randint(highest, lowest)


    def update(self) -> None:
        self.rect.x -= self._speed
        if self.rect.right < 0:
            self.kill()

    def get_item_id(self) -> str:
        return self._item_id

    def get_category(self) -> str:
        return self._category
    

# スポーン間隔(フレーム) と スポーン確率
ITEM_SPAWN_INTERVAL_STAGE1 = 90   # 1.5秒(60FPS想定)
ITEM_SPAWN_INTERVAL_STAGE2 = 70
ITEM_SPAWN_PROB_STAGE1 = 0.55
ITEM_SPAWN_PROB_STAGE2 = 0.65


def pick_weighted_item_id(item_defs: dict[str, ItemDef], stage: int) -> str:
    """
    item_defs の weight に基づいて item_id を1つ返す（重み付き抽選）。

    Args:
        item_defs: item_id -> ItemDef の辞書
        stage: 現状は抽選ロジックに影響しないが、将来ステージ別抽選に拡張できるため引数として保持

    Returns:
        str: 抽選された item_id
    """
    ids = list(item_defs.keys())
    weights = [max(0, item_defs[i].get_weight()) for i in ids]
    total = sum(weights)
    if total <= 0:
        # 全部0なら先頭
        return ids[0]

    r = random.randint(1, total)
    acc = 0
    for i, w in zip(ids, weights):
        acc += w
        if r <= acc:
            return i
    return ids[-1]


def maybe_spawn_item(tmr: int, stage: int, item_defs: dict[str, ItemDef], items: pg.sprite.Group) -> None:
    """
    アイテムをスポーンするかを判定し、スポーンする場合は items に追加する。

    - stage に応じてスポーン間隔(interval)と確率(prob)を切り替える
    - tmr が interval の倍数のタイミングのみ抽選する
    - 当選したら重み付き抽選で item_id を選ぶ
    """
    if stage == 1:
        interval = ITEM_SPAWN_INTERVAL_STAGE1
        prob = ITEM_SPAWN_PROB_STAGE1
    else:
        interval = ITEM_SPAWN_INTERVAL_STAGE2
        prob = ITEM_SPAWN_PROB_STAGE2

    if tmr % interval != 0:
        return

    if random.random() > prob:
        return

    item_id = pick_weighted_item_id(item_defs, stage)
    items.add(Item(item_defs[item_id], stage))
    
def apply_status_pickup(item_id: str, inv: Inventory, bird: Bird) -> None:
    """
    状態アイテム取得時の特殊ルールを適用する。

    仕様:
    - tabaco：所持中は二段ジャンプ不可（max_jump=1）
    - kinoko：
        - 無状態で取得 -> max_jump=3（状態は kinoko）
        - tabaco所持中に取得 -> tabacoを打ち消し無状態へ（max_jump=2）

    副作用:
    - inv の状態スロット（status）を書き換える
    - bird の最大ジャンプ回数を変更する
    """
    cur_status = inv.get_status()

    if item_id == "tabaco":
        inv.pickup_status_basic("tabaco")
        bird.set_max_jump(1)
        return

    if item_id == "kinoko":
        if cur_status == "tabaco":
            # 打ち消し：無状態へ戻す
            inv.clear_status()
            bird.set_max_jump(2)
            return
        else:
            inv.pickup_status_basic("kinoko")
            bird.set_max_jump(3)
            return

    # 他の状態アイテムが増えたらここに追加
    inv.pickup_status_basic(item_id)

def apply_status_from_current(inv: Inventory, bird: Bird) -> None:
    """
    ステージ切替などで、現在の所持状態に合わせてジャンプ数を再適用したい場合用
    """
    st = inv.get_status()
    if st == "tabaco":
        bird.set_max_jump(1)
    elif st == "kinoko":
        bird.set_max_jump(3)
    else:
        bird.set_max_jump(2)


# =========================
# メイン
# =========================
def main():
    pg.display.set_caption("こうかとんダンジョン")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    clock = pg.time.Clock()
    
   

    game_state = STATE_START
    state_timer = 0
    stage = 1
    params = stage_params(stage)
    bg = Background(params["bg_file"], params["bg_speed"])
    bird = Bird(3, (200, get_ground_y()))
    
    enemies = pg.sprite.Group()

    boss = None
    boss_active = False
    tmr = 0
    mid_boss_spawned = False
    mid_boss_defeated = False

    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT: return

            if event.type == pg.KEYDOWN:
                # ===== スタート画面 =====
                if game_state == STATE_START:
                    if event.key == pg.K_RETURN:
                        game_state = STATE_PLAY
                        tmr = 0  # タイマーリセット

            # ===== プレイ中 =====
                elif game_state == STATE_PLAY:
                    if event.key == pg.K_UP:
                        bird.try_jump()
                    if event.key == pg.K_ESCAPE: 
                        return
                    if event.key == pg.K_SPACE:
                        atk_id = inv.get_attack()
                    # 何も持ってなければ撃てない
                        if atk_id == "Beam":
                            beams.add(Beam((bird.get_rect().right + 30, bird.get_rect().centery)))
                        elif atk_id == "arrow":
                            arrows.add(Arrow((bird.get_rect().right + 30, bird.get_rect().centery)))

        screen.fill((0, 0, 0))
        # ========= 状態別処理 =========
        if game_state == STATE_START:
            draw_start_screen(screen)
        
        elif game_state == STATE_PLAY:
            # ---- 更新 ----
            bg.update(screen)
            if DEBUG_DRAW_GROUND_LINE:
                pg.draw.line(screen, (0, 0, 0), (0, get_ground_y()), (WIDTH, get_ground_y()), 2)

            bird.update(key_lst, screen)
            enemies.update()
            items.update()
            beams.update()
            arrows.update()
            exps.update()

            # ---- 描画 ----
            enemies.draw(screen)
            items.draw(screen)
            beams.draw(screen)
            arrows.draw(screen)
            exps.draw(screen)

        elif game_state == STATE_TO_FINAL:
            draw_to_final_screen(screen)

        elif game_state == STATE_CLEAR:
            draw_clear_screen(screen)

        elif game_state == STATE_GAMEOVER:
            draw_gameover_screen(screen)
        
                # bird を新しい地面Yへ合わせる（めり込み/浮きを防ぐ）
        bird.get_rect().bottom = get_ground_y()
        apply_status_from_current(inv, bird)
        enemies.empty()  # ★ステージ1の敵を消して、以後は2の画像だけ出す



        # 敵生成：複数流入（変更なし）
        if not mid_boss_spawned:
            if tmr % params["spawn_interval"] == 0:
                if random.random() <0.93:
                    spawn_enemy(enemies, stage)
            if bird.hp <= 0:
                game_state = STATE_GAMEOVER
            #他担当と連携
            if mid_boss_defeated:
                game_state = STATE_CLEAR

        if score > 500 and not mid_boss_spawned and not mid_boss_defeated:
            mid_boss_spawned = True
            enemies.empty()          # ★ モブ全消去
            boss_group.add(MidBoss())

        maybe_spawn_item(tmr, stage, ITEM_DEFS, items)

        hit1 = pg.sprite.groupcollide(enemies, beams, True, True) # ビーム当たり判定
        for emy in hit1.keys():
            exps.add(Explosion(emy.get_rect().center, life=30))
            score += random.randint(10,20)  # スコア加算

        hit2 = pg.sprite.groupcollide(enemies, arrows, True, True) # 矢当たり判定
        for emy in hit2.keys():
            exps.add(Explosion(emy.get_rect().center, life=30))
            score += random.randint(10,20)  # スコア加算

        picked = pg.sprite.spritecollide(bird, items, True) # アイテム取得判定
        for it in picked:
            item_id = it.get_item_id()
            cat = ITEM_DEFS[item_id].get_category()

            if cat == "attack": # 攻撃アイテム
                inv.pickup_attack(item_id)
            else:
                apply_status_pickup(item_id, inv, bird)
        
        items.update()  # ← 他の人のアイテム（右→左）は相手update内で動く想定

        # ===== 敵ダメージ（HP-20）=====
        if inv_tmr > 0:
            inv_tmr -= 1

        hit_list = pg.sprite.spritecollide(bird, enemies, False)
        if hit_list and inv_tmr == 0:
            hp = max(0, hp - DMG)

            if hp <= 0:
                return 0

            for e in hit_list:
                e.kill()

            dmg_popup_tmr = POPUP_FRAMES
            inv_tmr = INV_FRAMES

        # 描画（スプライト）
        items.draw(screen)


        # HPが0ならゲーム終了（任意）
        if bird.hp <= 0:
            return 0

        enemies.draw(screen)
        items.draw(screen)
        beams.draw(screen)
        beams_tbos.draw(screen)
        arrows.draw(screen)
        exps.draw(screen)

        # ===== UI：HP（左下）=====
        hp_pos = (20, HEIGHT - 50)
        hp_text = font.render(f"HP:{hp}", True, (255, 255, 255))
        screen.blit(hp_text, hp_pos)

        # HPバー（残りHPを緑）
        bar_x, bar_y = 20, HEIGHT - 25
        bar_w, bar_h = 200, 14
        pg.draw.rect(screen, (0, 0, 0), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4))
        pg.draw.rect(screen, (255, 255, 255), (bar_x, bar_y, bar_w, bar_h))
        hp_ratio = max(0, min(1, hp / HP_MAX))
        pg.draw.rect(screen, (0, 200, 0), (bar_x, bar_y, int(bar_w * hp_ratio), bar_h))

        # 「-20」赤表示（約2秒）
        if dmg_popup_tmr > 0:
            dmg_popup_tmr -= 1
            dmg_text = font.render(f"-{DMG}", True, (255, 0, 0))
            screen.blit(dmg_text, (hp_pos[0] + hp_text.get_width() + 10, hp_pos[1]))

        # ===== UI：Score（右上：白縁＋中黒）=====
        score_str = f"Score:{score}"
        tmp = font.render(score_str, True, (0, 0, 0))  # 幅取得用
        score_pos = (WIDTH - tmp.get_width() - 20, 20)
        draw_text_outline(screen, score_str, font, score_pos, (0, 0, 0), (255, 255, 255), outline_px=2)

        # ===== UI：右下 Attack / Status（黒塗り＋白枠）=====
        pg.draw.rect(screen, (0, 0, 0), attack_box)
        pg.draw.rect(screen, (255, 255, 255), attack_box, 2)
        pg.draw.rect(screen, (0, 0, 0), status_box)
        pg.draw.rect(screen, (255, 255, 255), status_box, 2)

        atk_label = font_ui.render("Attack", True, (255, 255, 255))
        sta_label = font_ui.render("Status", True, (255, 255, 255))
        screen.blit(atk_label, (attack_box.x + 10, attack_box.y + 8))
        screen.blit(sta_label, (status_box.x + 10, status_box.y + 8))

        # ---- invから現在装備を取得 ----
        atk_id = inv.get_attack()
        sta_id = inv.get_status()

        def draw_slot(box: pg.Rect, item_id: str | None) -> None:
            # 表示エリア（ラベルの下）
            pad_x = 12
            top_y = box.y + 34
            area = pg.Rect(box.x + pad_x, top_y, box.w - pad_x * 2, box.h - (top_y - box.y) - 10)

            if item_id is None:
                txt = font_item.render("-", True, (255, 255, 255))
                screen.blit(txt, (area.x, area.y + 10))
                return

            # アイコン
            icon = UI_ICONS[item_id]
            icon_y = area.y + (area.h - icon.get_height()) // 2
            screen.blit(icon, (area.x, icon_y))

            # 名前（長い場合は枠内に収まるように省略）
            name_x = area.x + icon.get_width() + 10
            max_w = area.right - name_x

            name_str = item_id
            txt = font_item.render(name_str, True, (255, 255, 255))
            if txt.get_width() > max_w:
                # 末尾を「...」にして収める
                base = name_str
                while len(base) > 1:
                    base = base[:-1]
                    name_str = base + "..."
                    txt = font_item.render(name_str, True, (255, 255, 255))
                    if txt.get_width() <= max_w:
                        break

            name_y = area.y + (area.h - txt.get_height()) // 2
            screen.blit(txt, (name_x, name_y))

        # 描画
        draw_slot(attack_box, atk_id)
        draw_slot(status_box, sta_id)
        
        if mid_boss_spawned:
            boss = boss_group.sprites()[0]

            # HPテキスト
            hp_text = font.render(f"HP:{boss.hp}", True, (255, 255, 255))
            screen.blit(
                hp_text,
                (boss.rect.centerx - hp_text.get_width() // 2,
                boss.rect.top - 30)
            )


        # 【中ボスの更新・描画エリア】
        if mid_boss_spawned:
            # プレイヤーの位置（bird.get_rect()）を渡して、狙いを定めさせる
            boss_group.update(bird.get_rect(), beams_tbos, meteors)
            
            # ビームと隕石も一緒に更新
            beams_tbos.update()
            meteors.update()
            
            # まとめて描画
            boss_group.draw(screen)
            beams_tbos.draw(screen)
            meteors.draw(screen)

            # ビームとの衝突判定（当たったらビームを消す）
        if pg.sprite.spritecollide(bird, beams_tbos, True):
            print("ビームがヒット！")  # ログ出力(仮)
            bird.set_damage()  # 追加：点滅開始


        # 隕石との衝突判定（当たったら隕石を消す）
        if pg.sprite.spritecollide(bird, meteors, True):
            print("隕石がヒット！")  # ログ出力(仮)
            bird.set_damage()  # 追加：点滅開始

        if mid_boss_spawned:
            boss = boss_group.sprites()[0]

            # ---- ビーム命中 ----
            hit_beams = pg.sprite.spritecollide(boss, beams, True)
            if hit_beams:
                boss.hp -= 100 * len(hit_beams)

            # ---- 矢命中 ----
            hit_arrows = pg.sprite.spritecollide(boss, arrows, True)
            if hit_arrows:
                boss.hp -= 80 * len(hit_arrows)

            # ---- 撃破判定 ----
            if boss.hp <= 0:
                exps.add(Explosion(boss.rect.center, life=60))

                boss.kill()                 # 中ボス消滅
                boss_group.empty()          # 念のため完全削除
                beams_tbos.empty()          # 中ボスビーム消去
                meteors.empty()             # 隕石消去

                mid_boss_spawned = False    # フラグOFF
                mid_boss_defeated = True
                score += 1000               # 撃破ボーナス

                            # 敵生成：複数流入
            if tmr % params["spawn_interval"] == 0:
                spawn_enemy(enemies, stage)
                if random.random() < 0.30:
                    spawn_enemy(enemies, stage)
            tmr += 1

        elif game_state == STATE_TO_FINAL:
            state_timer += 1
            draw_to_final_screen(screen)
            if state_timer > 120:
                stage = 2
                params = stage_params(stage)
                bg = Background(params["bg_file"], params["bg_speed"])
                bird.get_rect().bottom = get_ground_y()
                game_state = STATE_PLAY
                tmr = 0
                
        elif game_state == STATE_CLEAR:
            draw_clear_screen(screen)
        
        elif game_state == STATE_GAMEOVER:
            draw_gameover_screen(screen)

        if boss_active and boss:
            boss.update()
            if bird.rect.colliderect(boss.rect):
                if bird.get_vy() > 0 and bird.rect.bottom <= boss.rect.top + 20:
                    boss.on_hit()
            boss.draw(screen)

        pg.display.update()
        
        tmr += 1
        clock.tick(FPS)

if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
