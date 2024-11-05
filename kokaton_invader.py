import math
import os
import random
import sys
import time
import pygame as pg

KONAMI_COMMAND = [
    pg.K_UP, pg.K_UP, pg.K_DOWN, pg.K_DOWN, 
    pg.K_LEFT, pg.K_RIGHT, pg.K_LEFT, pg.K_RIGHT,
    pg.K_b, pg.K_a
]
TIMEOUT = 200  # タイムアウト間隔

# 現在の入力状態を追跡する変数
command_index = 0  # 現在のコマンドの位置
tmr = 0  # タイマー
command1 = False  # コマンドが成功したかのフラグ

WIDTH = 650  # ゲームウィンドウの幅
HEIGHT = 750 # ゲームウィンドウの高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内or画面外を判定し，真理値タプルを返す関数
    引数：こうかとんや爆弾，ビームなどのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    command_mode = {
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.8)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "nomal"
        self.hyper_life = 0
    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 0.8)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        global command1
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        sum_mv = [0, 0]
        if command1 == False:
            for k, mv in __class__.delta.items():
                if key_lst[k]:
                    sum_mv[0] += mv[0]
                    sum_mv[1] += mv[1]
        if command1 == True:
            for k, mv in __class__.command_mode.items():
                if key_lst[k]:
                    sum_mv[0] += mv[0]
                    sum_mv[1] += mv[1]
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)
        

class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    cooltime = 0

    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = (0, -1)
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 0.8)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10
        Beam.cooltime = 30

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()
    
    @classmethod
    def cooltime_update(cls):
        """
        ビームのクールタイムを減らす
        """
        if cls.cooltime > 0:
            cls.cooltime -= 1



class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.transform.rotozoom(pg.image.load(f"fig/alien{i}.png"), 0, 0.5) for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(10, WIDTH-10), 0
        self.vx, self.vy = 0, +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)
        

class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy",boss: "Boss", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 boss：爆弾を投下するボス
        引数3 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = 10  # 爆弾円の半径：10
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するbossから見た攻撃対象のbirdの方向を計算
        if boss:
            brad = 30
            self.image = pg.Surface((2*brad, 2*brad))
            color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
            pg.draw.circle(self.image, color, (brad, brad), brad)
            self.image.set_colorkey((0, 0, 0))
            self.rect = self.image.get_rect()
            self.vx, self.vy = calc_orientation(boss.rect, bird.rect)  
            self.rect.centerx = boss.rect.centerx
            self.rect.centery = boss.rect.centery+boss.rect.height//2
            self.speed = 4
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        else:
            self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
            self.rect.centerx = emy.rect.centerx
            self.rect.centery = emy.rect.centery+emy.rect.height//2
            self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()
        


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy|Boss", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Score():
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, 50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class Lv():
    """
    敵の出現頻度をレベルによって管理して表示するクラス
    """
    lv_dic = {0:300, 1:250, 2:200, 3:150, 4:100, 5:50}
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.lv = 0
        self.freq = 300
        self.image = self.font.render(f"Lv: {self.lv}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, 100

    def update(self, screen: pg.Surface, tmr):
        """
        レベルを時間経過によって変更して表示するクラス
        """
        if self.lv <5:
            self.lv = tmr//1000
        self.freq = Lv.lv_dic[self.lv]
        self.image = self.font.render(f"Lv: {self.lv}", 0, self.color)
        screen.blit(self.image, self.rect)

class Fontdraw(pg.sprite.Sprite):
    """
    文字を指定の位置に表示させるクラス
    """
    def __init__(self, txt: str, size: int, centerxy: tuple[int, int], color=(0, 0, 255)):
        """
        文字をを生成する
        引数1 txt：表示させる文字列
        引数2 size：大きさ
        引数3 centerxy：文字を表示させる真ん中の位置
        """
        super().__init__()
        font = pg.font.Font(None, size)
        self.image = font.render(txt , True, color)
        self.rect = self.image.get_rect()
        self.rect.centerx, self.rect.centery = centerxy

    def update(self):
        pass

class MP:
    """MP（マジックポイント）を表示・管理するクラス"""
    def __init__(self):
        self.font = pg.font.Font(None, 40)
        self.value = 0  # 初期MP値を0に設定

    def increase(self, amount=1):
        """MPを増やすメソッド"""
        self.value += amount
    
    def decrease(self, amount=3):
        """MPを減少させるメソッド"""
        if self.value >= amount:
            self.value -= amount
            return True
        return False

    def update(self, screen):
        """画面にMPを描画するメソッド"""
        mp_surf = self.font.render(f"MP: {self.value}", True, (0, 0, 255))  
        mp_rect = mp_surf.get_rect()
        mp_rect.topleft = (0,670)  
        screen.blit(mp_surf, mp_rect)

class BIGBeam(pg.sprite.Sprite):
    """強化ビーム1を管理するクラス"""
    def __init__(self, bird, big):
        super().__init__()
        self.image = pg.image.load(f"fig/beam.png").convert_alpha()
        self.image = pg.transform.scale(self.image, (50, 50))  
        self.image = pg.transform.rotate(self.image, big) 
        self.rect = self.image.get_rect()
        self.vx = math.cos(math.radians(big))
        self.vy = -math.sin(math.radians(big))
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10


    
    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class EnhancedImageBeam(pg.sprite.Sprite):
    """強化ビーム2を管理するクラス"""
    def __init__(self, bird, angle_offset):
        super().__init__()
        self.image = pg.image.load(f"fig/beam.png").convert_alpha()
        self.image = pg.transform.scale(self.image, (50, 50))  
        self.image = pg.transform.rotate(self.image, angle_offset) 
        self.rect = self.image.get_rect()
        self.vx = math.cos(math.radians(angle_offset))
        self.vy = -math.sin(math.radians(angle_offset))
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10


    
    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class StrongBeam(pg.sprite.Sprite):
    """MPを5消費して発射する、強力な大きいビーム"""
    def __init__(self, bird,offset):
        super().__init__()
        self.image = pg.image.load(f"fig/beam.png").convert_alpha()
        self.image = pg.transform.scale(self.image, (200,50))  
        self.image = pg.transform.rotate(self.image, offset) 
        self.rect = self.image.get_rect()
        self.vx = math.cos(math.radians(offset))
        self.vy = -math.sin(math.radians(offset))
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10
    
    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()

class Boss(pg.sprite.Sprite):
    """
    ボスに関するクラス
    """
    imgs = [pg.transform.rotozoom(pg.image.load(f"fig/alien{3}.png"), 0, 2)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH // 2, 0
        self.vx, self.vy = 0, +3
        self.bound = 100  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル
        self.hp = 100  # ボスの体力
        

    def update(self):
        """
        ボスを速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.move_ip(self.vx, self.vy)


    def draw_hp_bar(self, screen):
        """
        ボスのhpを表示する
        """
        bar_width = self.rect.width
        bar_height = 10
        fill_width = int(bar_width * (self.hp / 100))
        
        pg.draw.rect(screen, (255, 0, 0), (self.rect.left - 150, self.rect.top - 20, 3 * bar_width, bar_height))
        # 背景の赤いバー
        pg.draw.rect(screen, (0, 255, 0), (self.rect.left - 150, self.rect.top - 20, 3 * fill_width, bar_height))
        # HPに応じた緑色のバー


class Scorerank():
    """
    スコアランキングを管理するクラス
    """
    def __init__(self, path: str):
        """
        ランキングが記録されたファイルを読み込む
        ない場合は新たに作成する
        引数1 ファイルのパス
        """
        self.path = path
        try:
            with open(path, "r", encoding="utf-8") as rf:
                txt = rf.read()
        except FileNotFoundError: #ファイルが見つからなかったら
            txt = "0,0,0,0,0,0,0,0,0,0" #10個の0点の文字列作成
            with open(path, "w", encoding="utf-8") as wf:
                wf.write(txt)
        self.ranklst = [int(i) for i in txt.split(",")] #int型のリストに変換
    
    def update(self, score:int):
        self.ranklst.append(score) #新しいスコアをリストに追加してソートする
        self.ranklst.sort(reverse=True)
        self.ranklst.pop(-1) #1つ増えた分減らす
        with open(self.path, "w", encoding="utf-8") as wf:
                wf.write(','.join(map(str, self.ranklst))) #,で区切られた文字列に直して書き込む
        

def check_konami_command(key_lst):
    """
    コマンドが入力されたかを確認する関数
    引数 key_lst:現在のキー入力状態リスト
    """
    global command_index, tmr, command1
    if command1 == True:
        pass
    if command1 == False:
        # 指定したコマンドのキーが押されているかを確認
        if key_lst[KONAMI_COMMAND[command_index]]:
            command_index += 1  # 次のコマンドに進む
            print(f"Command step: {command_index}")
            tmr = 0  # タイマーをリセット

            # コマンドがすべて成功した場合
            if command_index == len(KONAMI_COMMAND):
                command1 = True
                command_index = 0  # コマンドの位置をリセット
                print("Konami Command Activated!")
        elif tmr >= TIMEOUT:  # タイムアウト条件
            command_index = 0  # コマンドの位置をリセット


def main():
    global command1
    pg.display.set_caption("真！こうかとん無双")
    pg.display.set_caption("こうかとんインベーダー")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    flag = "start" #画面推移の管理
    rank = Scorerank("kokaton_invader_score.txt") #ファイルパスを渡してランクの作成
    while True:
        if flag =="start":
            bg_img = pg.image.load(f"fig/pg_bg.jpg")
            txts = pg.sprite.Group()
            title_text = Fontdraw(f"kokaton defender", 80, (WIDTH // 2, 200))
            start_text = Fontdraw("start", 60, (WIDTH // 2, HEIGHT // 2))
            rank_text = Fontdraw("ranking", 60, (WIDTH // 2, HEIGHT // 2 + 60))
            txts.add(title_text)
            txts.add(start_text)
            txts.add(rank_text)
            img = pg.image.load("fig/9.png")
            img = pg.transform.rotozoom(img, 0, 1.0)
            img_rect = img.get_rect()
            selection_index = 0
            options = [start_text, rank_text]
            while True:
                screen.blit(bg_img, [0, 0])
                txts.draw(screen)
                selected_text = options[selection_index % len(options)]
                img_rect.right = selected_text.rect.left - 10
                img_rect.centery = selected_text.rect.centery
                screen.blit(img, img_rect)
                pg.display.update()
                for event in pg.event.get():
                    if event.type == pg.QUIT:
                        return 0
                    elif event.type == pg.KEYDOWN:
                        if event.key == pg.K_UP:
                            selection_index = (selection_index - 1) % len(options)
                        elif event.key == pg.K_DOWN:
                            selection_index = (selection_index + 1) % len(options)
                        elif event.key == pg.K_RETURN:
                            if selection_index % len(options)== 0:
                                flag = "game"
                            elif selection_index % len(options) == 1:
                                flag = "rank"
                            break
                if flag == "game" or flag == "rank":
                    break
            continue
        
        if flag == "rank": #ランク画面なら
            screen = pg.display.set_mode((WIDTH, HEIGHT))
            bg_img = pg.image.load(f"fig/pg_bg.jpg")
            txts = pg.sprite.Group()
            txts.add(Fontdraw("RANKING", 60, (WIDTH // 2, 80)))
            txts.add(Fontdraw("home[h]", 60, (WIDTH // 2, 680)))
            for i, score in enumerate(rank.ranklst): #ランキングの表示
                txts.add(Fontdraw(f"No.{i+1} : {score}", 50, (WIDTH // 2, 150 + i*50 )))
            screen.blit(bg_img, [0, 0])
            txts.draw(screen)
            pg.display.update()
            while True:
                key_lst = pg.key.get_pressed()
                for event in pg.event.get():
                    if event.type == pg.QUIT:
                        return 0
                if key_lst[pg.K_h]:
                    flag = "start"
                    break 

        if flag =="gameover":
            bg_img = pg.image.load(f"fig/pg_bg.jpg")
            txts = pg.sprite.Group()
            txts.add(Fontdraw(f"HiScore : {rank.ranklst[0]}", 50, (WIDTH // 2, 250)))
            score_text = Fontdraw(f"Score:{score.value}", 80, (WIDTH // 2, 200))
            start_text = Fontdraw("start", 60, (WIDTH // 2, HEIGHT // 2))
            home_text = Fontdraw("home", 60, (WIDTH // 2, HEIGHT // 2 + 60))
            txts.add(score_text)
            txts.add(start_text)
            txts.add(home_text)
            img = pg.image.load("fig/9.png")
            img = pg.transform.rotozoom(img, 0, 1.0)
            img_rect = img.get_rect()
            selection_index = 0
            options = [start_text, home_text]
            while True:
                screen.blit(bg_img, [0, 0])
                txts.draw(screen)
                selected_text = options[selection_index % len(options)]
                img_rect.right = selected_text.rect.left - 10
                img_rect.centery = selected_text.rect.centery
                screen.blit(img, img_rect)
                pg.display.update()
                for event in pg.event.get():
                    if event.type == pg.QUIT:
                        return 0
                    elif event.type == pg.KEYDOWN:
                        if event.key == pg.K_UP:
                            selection_index = (selection_index - 1) % len(options)
                        elif event.key == pg.K_DOWN:
                            selection_index = (selection_index + 1) % len(options)
                        elif event.key == pg.K_RETURN:
                            if selection_index % len(options)== 0:
                                flag = "game"
                            elif selection_index % len(options) == 1:
                                flag = "start"
                            break
                if flag == "game" or flag == "start":
                    break
            continue
        if flag == "game":
            bg_img = pg.image.load(f"fig/pg_bg.jpg")
            score = Score()
            lv = Lv()
            mp = MP()  # MPインスタンスの作成
            boss_spown = False  # ボスの出現判定
            boss_span = 0  # ボスの出現スパン
            
            bird = Bird(3, (325, 650))
            bombs = pg.sprite.Group()
            beams = pg.sprite.Group()
            BIG_beams =pg.sprite.Group()
            enhanced_image_beams = pg.sprite.Group()
            Strong_Beam = pg.sprite.Group()
            exps = pg.sprite.Group()
            emys = pg.sprite.Group()
            bosses = pg.sprite.Group()

            tmr = 0
            command1 = False
            clock = pg.time.Clock()


            while True:
                key_lst = pg.key.get_pressed()
                check_konami_command(key_lst)
                for event in pg.event.get():
                    if event.type == pg.QUIT:
                        return 0
                    if event.type == pg.KEYDOWN and event.key == pg.K_SPACE and Beam.cooltime == 0:
                        beams.add(Beam(bird))

                    if event.type == pg.KEYDOWN and event.key == pg.K_e:  # 強化ビーム発動キー "E"
                        if mp.decrease(1): 
                            # 3方向にビームを発射
                            BIG_beams.add(BIGBeam(bird, big=80))
                            BIG_beams.add(BIGBeam(bird, big=90))
                            BIG_beams.add(BIGBeam(bird, big=100))

                    if event.type == pg.KEYDOWN and event.key == pg.K_w:  # 強化ビーム発動キー "W"
                        if mp.decrease(5): 
                            # 5方向にビームを発射
                            enhanced_image_beams.add(EnhancedImageBeam(bird, angle_offset=70))
                            enhanced_image_beams.add(EnhancedImageBeam(bird, angle_offset=80))
                            enhanced_image_beams.add(EnhancedImageBeam(bird, angle_offset=90))
                            enhanced_image_beams.add(EnhancedImageBeam(bird, angle_offset=100))
                            enhanced_image_beams.add(EnhancedImageBeam(bird, angle_offset=110))

                    if event.type == pg.KEYDOWN and event.key == pg.K_q:  # 強化ビーム発動キー "Q"
                        if mp.decrease(7): 
                            Strong_Beam.add(StrongBeam(bird, offset=90))
                            Strong_Beam.add(StrongBeam(bird, offset=80))
                            Strong_Beam.add(StrongBeam(bird, offset=100))
                screen.blit(bg_img, [0, 0])
                boss_score = (score.value // 100) * 100
                if boss_score != boss_span:
                    boss_spown = False
                    boss_span = boss_score

                if tmr%lv.freq == 0:
                    emys.add(Enemy())

                for emy in emys:
                    if emy.state == "stop" and tmr%emy.interval == 0:
                        # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                        bombs.add(Bomb(emy,None,bird))
                
                if  score.value >= 100 and not boss_spown:
                    boss_spown = True
                    bosses.add(Boss())

                for boss in bosses:
                    if boss.state == "stop" and tmr%boss.interval == 0:
                        # ボスが停止状態に入ったら、intervalに応じて爆弾投下
                        bombs.add(Bomb(emy,boss,bird))

                for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
                    exps.add(Explosion(emy, 100))  # 爆発エフェクト
                    score.value += 10  # 10点アップ
                    mp.increase(1)  # MPを1増加
                    bird.change_img(6, screen)  # こうかとん喜びエフェクト

                for emy in pg.sprite.groupcollide(emys, BIG_beams,  True, True).keys():
                    exps.add(Explosion(emy, 100))  # 爆発エフェクト
                    score.value += 10  # 10点アップ
                    bird.change_img(6, screen)

                for emy in pg.sprite.groupcollide(emys, enhanced_image_beams,  True, True).keys():
                    exps.add(Explosion(emy, 100))  # 爆発エフェクト
                    score.value += 10  # 10点アップ
                    bird.change_img(6, screen)  # こうかとん喜びエフェクト

                for emy in pg.sprite.groupcollide(emys, Strong_Beam,  True, False).keys():
                    exps.add(Explosion(emy, 100))  # 爆発エフェクト
                    score.value += 10  # 10点アップ
                    bird.change_img(6, screen)  # こうかとん喜びエフェクト

                for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
                    exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                    score.value += 1  # 1点アップ

                for boss in pg.sprite.groupcollide(bosses, beams, None, True).keys():
                    if boss.hp <= 10:
                        exps.add(Explosion(boss, 50))  # 爆発エフェクト
                        score.value += 50  # 50点アップ
                        boss.kill()
                    elif boss.hp > 0:  # ボスの体力が0より大きかったら
                        boss.hp -= 10  # ボスの体力を10減らす

                for bomb in pg.sprite.groupcollide(bombs, enhanced_image_beams, True, False).keys():
                    exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                    score.value += 1  # 1点アップ

                for bomb in pg.sprite.groupcollide(bombs, BIG_beams, True, True).keys():
                    exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                    score.value += 1  # 1点アップ
                
                for bomb in pg.sprite.groupcollide(bombs,Strong_Beam , True, False).keys():
                    exps.add(Explosion(bomb, 50))  # 爆発エフェクト
                    score.value += 1  # 1点アップ

                for bomb in pg.sprite.groupcollide(bosses, enhanced_image_beams, None, False).keys():
                    if boss.hp <= 10:
                        exps.add(Explosion(boss, 50))  # 爆発エフェクト
                        score.value += 50  # 50点アップ
                        boss.kill()
                    elif boss.hp > 0:  # ボスの体力が0より大きかったら
                        boss.hp -= 0.5  # ボスの体力を10減らす

                for bomb in pg.sprite.groupcollide(bosses, BIG_beams, None, True).keys():
                    if boss.hp <= 10:
                        exps.add(Explosion(boss, 50))  # 爆発エフェクト
                        score.value += 50  # 50点アップ
                        boss.kill()
                    elif boss.hp > 0:  # ボスの体力が0より大きかったら
                        boss.hp -= 5  # ボスの体力を10減らす
                
                for bomb in pg.sprite.groupcollide(bosses,Strong_Beam , None, False).keys():
                    if boss.hp <= 10:
                        exps.add(Explosion(boss, 50))  # 爆発エフェクト
                        score.value += 50  # 50点アップ
                        boss.kill()
                    elif boss.hp > 0:  # ボスの体力が0より大きかったら
                        boss.hp -= 0.8  # ボスの体力を10減らす

                if len(pg.sprite.spritecollide(bird, bombs, True)) != 0:
                    bird.change_img(8, screen) # こうかとん悲しみエフェクト
                    score.update(screen)
                    pg.display.update()
                    time.sleep(2)
                    flag = "gameover"
                    rank.update(score.value)
                    break
                
                bosses.update()
                bosses.draw(screen)
                for boss in bosses:
                    boss.update()
                    boss.draw_hp_bar(screen)
                bird.update(key_lst, screen)
                beams.update()
                beams.draw(screen)
                BIG_beams.update()# 強化ビーム1の更新
                BIG_beams.draw(screen)# 強化ビーム1の描画
                enhanced_image_beams.update()  # 強化ビーム2の更新
                enhanced_image_beams.draw(screen)  # 強化ビーム2の描画
                Strong_Beam.update()
                Strong_Beam.draw(screen)
                emys.update()
                emys.draw(screen)
                bombs.update()
                bombs.draw(screen)
                exps.update()
                exps.draw(screen)
                score.update(screen)
                score.update(screen)  # スコアを更新
                mp.update(screen)  # MPを更新
                lv.update(screen, tmr)
                pg.display.update()
                Beam.cooltime_update()
                tmr += 1
                clock.tick(50)

if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
