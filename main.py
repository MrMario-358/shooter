from kivy.uix.accordion import StringProperty
from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivy import platform
from kivy.core.window import Window
from kivy.clock import Clock
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.metrics import dp
from kivy.uix.image import Image
from random import randint
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivy.core.window import Keyboard
from kivy.properties import StringProperty
from kivy.properties import NumericProperty
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.fitimage import FitImage

FPS = 120

BULLET_SPEED = dp(10)
SHIP_SPEED = dp(5)

DIRECTION_UP = 1
DIRECTION_DOWN = -1

SPAWN_ENEMY_TIME = 2

HP_MAX = 10
FIRE_RATE_MIN = 0.5  # Мінімальний час між пострілами (найшвидша стрільба)
FIRE_RATE_MEDIUM = 3  # Середній час між пострілами

class MainScreen(MDScreen):
    ...
class Shot(MDBoxLayout):
    source_image = StringProperty("assets/images/ship.png")
    def __init__(self, direction,owner, source_image=None, **kwargs):
        super().__init__(**kwargs)
        self.direction = direction
        if source_image:
            self.source_image = source_image
        self.owner = owner 
        

class Ship(Image):
    hp = NumericProperty()
    max_hp = NumericProperty
    def __init__(self, direction=DIRECTION_UP, hp=HP_MAX, fire_rate=FIRE_RATE_MEDIUM, **kwargs):
        super().__init__(**kwargs)
        self.direction = direction
        self.hp = self.max_hp = hp
        self.fire_rate = fire_rate
        self._last_shot = self.fire_rate
        self.anim_delay = 0.05
        self._last_anim = self.anim_delay
        self.current_anim = 0
    
    def on_kv_post(self,base_widget):
        self.images = [self.source]
        return super().on_kv_post(base_widget)
        
    def moveLeft(self):
        if self.x - SHIP_SPEED >= 0:
            self.x -= SHIP_SPEED
        else:
            self.x = 0

    def moveRight(self):
        if self.x + SHIP_SPEED <= self.parent.width - self.width:
            self.x += SHIP_SPEED
        else:
            self.x = self.parent.width - self.width

    def shot(self):
        # Перевірка: чи минув необхідний час з моменту останнього пострілу
        if self._last_shot < self.fire_rate:
            return  # Ще не час — виходимо без пострілу 
        self._last_shot = 0
        
        image = (
            "assets/images/ship.png"
            if self.direction == DIRECTION_UP
            else "assets/images/shoot.png"
        )
        shot = Shot(self.direction, owner = self, source_image=image)
        shot.center_x = self.center_x
        shot.y = self.top - dp(90) if self.direction == DIRECTION_UP else self.y - shot.height
        self.game_screen.bullets.append(shot)
        self.game_screen.ids.front.add_widget(shot)

    def update(self, dt):
        self._last_shot += dt
        self.animation(dt) 
    
    def animation(self, dt):
        if len(self.images) > 1:
            if self._last_anim >= self.anim_delay:
                self.source = self.images[self.current_anim]

                if (len(self.images) > self.current_anim + 1):
                    self.current_anim += 1
                else:
                    self.current_anim = 0
                
                self._last_anim = 0

            self._last_anim += dt

class PlayerShip(Ship):
    def __init__(self, **kwargs):
        super().__init__(direction=DIRECTION_UP, fire_rate=FIRE_RATE_MIN, **kwargs)

    def on_kv_post(self,base_widget):
        super().on_kv_post(base_widget)
        self.images.extend(["assets/images/ruketa2.webp","assets/images/roketa1.png","assets/images/ruketa.webp"])
    
    def update(self, keys, dt):
        super().update(dt)
        
        for key in keys:
            if keys[key] == True:
                if key == "left" and self.center_x > 0:
                    self.moveLeft()
                if key == "right" and self.center_x < Window.width:
                    self.moveRight()
                if key == "shot":
                    self.shot()
                    keys[key] = False

class EnemyShip(Ship):
    def __init__(self, speed=dp(3), *args, **kwargs):
        super().__init__(direction=DIRECTION_DOWN, *args, **kwargs)
        self.frame = 0
        self.speed = speed

    def update(self, dt):
        super().update(dt)
        self.pos[1] -= self.speed
        if self.frame % 100 == 0:
            self.shot()
        self.frame += 1
        
# ПАРАЛАКС-ФОН
class MoveBackground(MDFloatLayout):
    """
    Два екземпляри одного зображення розміщуються один над одним.
    При русі вниз, коли верхня картинка виходить за нижній край —
    вона телепортується вгору, створюючи ефект нескінченної прокрутки (parallax).
    """

    def __init__(self, source, speed=dp(1), scale=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speed = speed
        # Перший екземпляр — починається з позиції (0, 0)
        self.add_widget(FitImage(source=source, size_hint_y=scale))
        # Другий екземпляр — розміщується одразу над першим (поза екраном вгорі)
        self.add_widget( FitImage(source=source, size_hint_y=scale, pos=(0, Window.size[1] * scale)))

    def move(self):
        """
        Викликається кожен кадр з GameScreen.update().
        Зміщує обидва зображення вниз на self.speed пікселів.
        Якщо зображення повністю вийшло за нижній край — повертає його вгору.
        """
        for img in self.children:
            img.pos[1] -= self.speed
            if img.top <= 0:  # Зображення повністю зникло з екрану
                # Телепортуємо вгору
                img.pos[1] = Window.size[1]  # завжди на висоту екрану
    
class GameScreen(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #Clock.schedule_interval(self.update, 1 / FPS)
        self.event_keys = {}
        self.enemy_ships = []
        self.bullets = []
        self.pause_menu =[]
        self.ship = self.ids.ship
        self.ship.game_screen = self
        self.spawn_delay = SPAWN_ENEMY_TIME
        self.time_last_spawn = 0
        self.backBack = MoveBackground(source="assets/images/photo_2026-04-27_21-13-45.jpg", speed=0.2)
        self.backFront = MoveBackground(source="assets/images/photo_2026-04-27_21-05-43.jpg", speed=1, scale=3)
        self.ids.back.add_widget(self.backBack)
        self.ids.back.add_widget(self.backFront)
        
        
        Window.bind(on_key_down = self._on_key_down)
        Window.bind(on_key_up = self._on_key_up)
            
    def on_enter(self, *args):
        self.update_event = Clock.schedule_interval(self.update, 1 / FPS)
        self.ship = self.ids.ship

        return super().on_enter(*args)
    
    def spawn_enemy(self):
        enemy = EnemyShip(1)
        enemy.pos = (randint(0, int(Window.size[0] - enemy.size[0])), Window.size[1])
        enemy.game_screen = self
        self.enemy_ships.append(enemy)
        self.ids.front.add_widget(enemy)

        
    def update(self, dt):
        # Головний корабель
        self.ship.update(self.event_keys,dt)

        # вороги - спавн кожні [self.spawn_delay] секунд
        self.time_last_spawn += dt
        if self.time_last_spawn >= self.spawn_delay:
            self.spawn_enemy()
            self.time_last_spawn = 0

        # вороги - рух
        for ship in self.enemy_ships[:]:
            ship.update(dt)
            if ship.top < 0:
                self.enemy_ships.remove(ship)
                self.ids.front.remove_widget(ship)

            # колізія з гравцем 
            if ship.collide_widget(self.ship):
                self.game_over()
        

        # Керування кулями
        self.manage_bullets()
        
        self.backBack.move()
        self.backFront.move()
        
    # Рух всіх куль гри
    def manage_bullets(self):
        for bullet in self.bullets[:]:
            bullet.y += BULLET_SPEED * bullet.direction
            self.check_collisions(bullet)

            # Видалення куль при виході за рамки вікна
            if bullet.y > Window.height or bullet.top < 0:
                self.ids.front.remove_widget(bullet)
                self.bullets.remove(bullet)
    
    def check_collisions(self, bullet):
        if bullet.owner == self.ship:
            # перевіряємо потрапляння у ворога
            for enemy in self.enemy_ships[:]:
                if bullet.collide_widget(enemy):
                    self.enemy_ships.remove(enemy)
                    self.ids.front.remove_widget(enemy)

                    self.remove_bullet(bullet)
                    break
        else:
            # перевіряємо потрапляння у гравця
            if bullet.collide_widget(self.ship):
                self.ship.hp -= 1
                print(self.ship.hp)  # Debug-вивід для тестування

                if self.ship.hp <= 0:
                    self.game_over()  # Якщо HP вичерпано — кінець гри
                self.remove_bullet(bullet)
                
    def remove_bullet(self, bullet):
        if bullet in self.bullets:
            self.bullets.remove(bullet)
            self.ids.front.remove_widget(bullet)

    def game_over(self):
        self.update_event.cancel()
        # Видалення ворогів
        for enemy in self.enemy_ships[:]:
            self.enemy_ships.remove(enemy)
            self.ids.front.remove_widget(enemy)
        # Видалення куль
        for bullet in self.bullets[:]:
            self.ids.front.remove_widget(bullet)
            self.bullets.remove(bullet)

        self.manager.current = 'game_over'

    def pressKey(self, key):
        self.event_keys[key] = True

    def releaseKey(self, key):
        self.event_keys[key] = False

    def show_menu(self):
        self.update_event.cancel()

        if not self.pause_menu:
            self.pause_menu = MDDialog(
                title="Game Paused",
                text="Resume the game?",
                on_dismiss=self.resumeGame,
                buttons=[
                    MDFlatButton(
                        text="RESUME",
                        theme_text_color="Custom",
                        text_color=app.theme_cls.primary_color,
                        on_press=self.pauseStop,
                    )
                ],
            )
        self.pause_menu.open()

    def pauseStop(self, *args):
        self.pause_menu.dismiss()

    def resumeGame(self, *args):
        self.update_event = Clock.schedule_interval(self.update, 1 / FPS)

    # Керування з клавіатури під час тестування з комп'ютера
    def _on_key_down(self, window, keycode, *args, **kwargs):
        key = Keyboard.keycode_to_string(window, keycode)
        if key == "spacebar":
            key = "shot"

        self.event_keys[key] = True

    def _on_key_up(self, window, keycode, *args, **kwargs):
        key = Keyboard.keycode_to_string(window, keycode)
        if key == "spacebar":
            key = "shot"

        self.event_keys[key] = False
        
class GameOverScreen(MDScreen):
    ...
        
class ShooterApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Orange"

        self.sm = MDScreenManager()

        self.sm.add_widget(MainScreen(name='main'))
        self.sm.add_widget(GameScreen(name='game'))
        self.sm.add_widget(GameOverScreen(name='game_over'))

        return self.sm
    
if platform != 'android':
    Window.size = (450, 700)
    Window.top = 100
    Window.left = 600
     
app = ShooterApp()
app.run()    