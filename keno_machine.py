import kivy
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.properties import BooleanProperty, StringProperty, ListProperty
from kivy.core.text import Label as CoreLabel
from kivy.metrics import sp

from functools import partial
import random

from gpiozero import LED
from gpiozero import Button as IOButton

import math, wave, struct, os, tempfile
import pygame

#---Aesthetic Vars---

gamePurple = (.5,.15,.6,1)
gameGreen  = get_color_from_hex("#1D9900")
gameOrange = get_color_from_hex("#FB4300")
gamePink   = get_color_from_hex("#F41771")
gameYellow = get_color_from_hex("#F4DF18")
gameBlue = get_color_from_hex("#0000F8")
gameRed = get_color_from_hex("#D0000B")
gameGrey = get_color_from_hex("#7A8083")

#---Custom Widgets---

def set_bg(widget, rgba=gameYellow):
    with widget.canvas.before:
        color = Color(*rgba)
        rect = Rectangle(pos=widget.pos, size=widget.size)

    def _update_rect(*args):
        rect.pos = widget.pos
        rect.size = widget.size

    widget.bind(pos=_update_rect, size=_update_rect)
    return color, rect

def info_label(text, color=(1,1,1,1)):
	lbl = Label(text=text, font_size='13dp', halign='left', valign='middle',color=color)
	lbl.bind(size=lambda inst, val: setattr(inst, 'text_size', inst.size))
	return lbl

def win_label(text):
        lbl = Label(text=text, font_size='30dp', color=gameRed, outline_color=gameYellow, outline_width=1, bold=True, halign='left', valign='middle')
        lbl.bind(size=lambda inst, val: setattr(inst, 'text_size', inst.size))
        return lbl

def credit_label(text):
        lbl = Label(text=text, font_size='30dp', color=gameRed, outline_color=gameYellow, outline_width=1, bold=True, halign='right', valign='middle')
        lbl.bind(size=lambda inst, val: setattr(inst, 'text_size', inst.size))
        return lbl


EB4 = 311.13*1.5
EB5 = 311.13*2.2
def make_wav(path, freq, duration=0.06, sr=44100, volume=0.4):
	n = int(sr * duration)
	attack = int(sr * 0.005)
	release = int(sr * 0.015)

	with wave.open(path, 'wb') as wf:
		wf.setnchannels(1)
		wf.setsampwidth(2)
		wf.setframerate(sr)

		frames = bytearray()
		for i in range(n):
			t = i / sr
			s = math.sin(2 * math.pi * freq * t)

			env = 1.0
			if i < attack:
				env = i / attack
			elif i > n - release:
				env = max(0.0, (n - i) / release)

			sample = int(32767 * volume * env * s)
			frames += struct.pack('<h', sample)

		wf.writeframes(frames)


class ColoredLabel(Button):
	def __init__(self, bg_rgba=(0,0,1,1), **kwargs):
		super().__init__(**kwargs)
		with self.canvas.before:
			self.bg = Color(*bg_rgba)
			self.rect = Rectangle(size=self.size, pos=self.pos)

		self.bind(pos=self.update_rect, size=self.update_rect)

	def update_rect(self, *args):
		self.rect.pos = self.pos
		self.rect.size = self.size

	def set_bg(self, rgba):
		self.bg.rgba = rgba

class KenoButton(Button):
	is_marked=BooleanProperty(False)
	marked_text=StringProperty("")
	marked_text_color=ListProperty([0,0,0,1])
	ball_color=ListProperty([1,1,1,1])

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		with self.canvas.after:
			self._ball_color_instr = Color(1,1,1,0)
			self._ball_ellipse = Ellipse(pos=self.pos, size=(0,0))

			self._text_color_instr=Color(0,0,0,0)
			self._text_rect=Rectangle(pos=self.pos,size=(0,0))

		self._core_label = CoreLabel(text="", font_size=sp(20), bold=True)
		self.bind(pos=self._update_ball, size=self._update_ball)
		self.bind(is_marked=self._update_ball, marked_text=self._update_ball, ball_color=self._update_ball, marked_text_color=self._update_ball)

	def _update_ball(self, *args):
		d = min(self.width, self.height) * 0.9
		x = self.x + (self.width - d) / 2
		y = self.y + (self.height - d) / 2
		self._ball_ellipse.pos=(x,y)
		self._ball_ellipse.size=(d,d)

		if self.is_marked and self.marked_text:
			self._ball_color_instr.rgba=self.ball_color

			self._core_label.text = self.marked_text
			self._core_label.font_size = d * 0.55
			self._core_label.refresh()
			tex = self._core_label.texture

			self._text_color_instr.rgba = self.marked_text_color

			tx = x + (d - tex.size[0]) / 2
			ty = y + (d - tex.size[1]) / 2
			self._text_rect.texture = tex
			self._text_rect.pos = (tx, ty)
			self._text_rect.size = tex.size

		else:
			self._ball_color_instr.rgba = (1, 1, 1, 0)
			self._text_color_instr.rgba = (1, 1, 1, 0)
			self._text_rect.size = (0, 0)


class Fourcard(BoxLayout):

	def __init__(self, **kwargs):
		super(Fourcard, self).__init__(**kwargs)
		self.orientation = "vertical"
		self.padding = [20,10,20,10]

		#---LED INIT--- (left to right)
		self.leds = [LED(16), LED(25), LED(23), LED(19), LED(6), LED(22), LED(17)]

		#---Button INIT---
		btime=0.1
		self.buttons = [IOButton(12,pull_up=True,bounce_time=0.1), IOButton(24,pull_up=True,bounce_time=btime), IOButton(18,pull_up=True,bounce_time=btime), IOButton(13,pull_up=True,bounce_time=btime), IOButton(5,pull_up=True,bounce_time=btime), IOButton(27,pull_up=True,bounce_time=btime), IOButton(4,pull_up=True,bounce_time=btime)]
		for i, button in enumerate(self.buttons):
			button.when_pressed = lambda i=i: self.buttonPushed(i)

		#---Game Vars---

		self.ready=True
		self.spinning=False
		self.paying=False
		self.auto_on=False

		self.credits=800.00
		self.denom=0.25
		self.speed=1
		self.LOCKED_speed_times=[0.3,0.16,0.1]
		self.speed_times=[0.3,0.16,0.1]

		self.drawnNums = ()

		self.current_card = 4
		self.picked_nums=[]
		self.marked_spots=[[],[],[],[]]

		self.hit_counts=[0,0,0,0]

		self.max_bet = 4
		self.bets=[0,0,0,0]
		self.total_bet=0

		self.wins=[0,0,0,0]
		self.payout_speed=0.08

		self.pay_table=[
			[0], #0-spot
			[0],    #1-spot
			[0,0,15],
			[0,0,2,46],
			[0,0,2,5,91],
			[0,0,0,3,12,810],
			[0,0,0,3,4,70,1600],
			[0,0,0,1,2,21,400,7000],
			[0,0,0,0,2,12,98,1652,10000],
			[0,0,0,0,1,6,44,335,4700,10000],
			[0,0,0,0,0,5,24,142,1000,4500,10000]
			]

		pygame.mixer.init(frequency=44100, channels=1)
		tmpdir = tempfile.gettempdir()
		boop_low_path  = os.path.join(tmpdir, "boop_eb4.wav")
		boop_high_path = os.path.join(tmpdir, "boop_eb5.wav")
		make_wav(boop_low_path,  EB4)
		make_wav(boop_high_path, EB5)

		self.boop_low  = pygame.mixer.Sound(boop_low_path)
		self.boop_high = pygame.mixer.Sound(boop_high_path)

		#SHELLS
		upper_game_shell = BoxLayout(orientation="horizontal", size_hint=(1, 0.8), spacing=10)
		upper_left_shell = BoxLayout(orientation="vertical", size_hint=(.34, 1), spacing=8)
		a_card_shell = BoxLayout(orientation="horizontal",spacing=8)
		a_card_title_shell = BoxLayout(orientation="vertical", size_hint=(.2, 1),spacing=-20)
		a_card_info_shell = BoxLayout(orientation="vertical", size_hint=(.8, 1))
		b_card_shell = BoxLayout(orientation="horizontal",spacing=8)
		b_card_title_shell = BoxLayout(orientation="vertical", size_hint=(.2, 1),spacing=-20)
		b_card_info_shell = BoxLayout(orientation="vertical", size_hint=(.8, 1))
		c_card_shell = BoxLayout(orientation="horizontal",spacing=8)
		c_card_title_shell = BoxLayout(orientation="vertical", size_hint=(.2, 1),spacing=-20)
		c_card_info_shell = BoxLayout(orientation="vertical", size_hint=(.8, 1))
		d_card_shell = BoxLayout(orientation="horizontal",spacing=8)
		d_card_title_shell = BoxLayout(orientation="vertical", size_hint=(.2, 1),spacing=-20)
		d_card_info_shell = BoxLayout(orientation="vertical", size_hint=(.8, 1))
		upper_right_shell = BoxLayout(orientation="vertical", size_hint=(.66, 1), spacing=10)
		card_buttons_shell = BoxLayout(orientation="horizontal", size_hint=(1, 0.08), spacing=8)
		keno_board_shell = BoxLayout(orientation="vertical", size_hint=(1, 0.92), spacing=20)
		keno_board_top_shell = GridLayout(cols=10, spacing=3, padding=[3])
		keno_board_bottom_shell = GridLayout(cols=10, spacing=3, padding=[3])
		lower_game_shell = BoxLayout(orientation="horizontal", size_hint=(1, 0.2))
		lower_left_shell = BoxLayout(orientation="vertical", size_hint=(0.43, 1))
		lower_left_win_shell = BoxLayout(orientation="horizontal")
		lower_left_buttons_shell = BoxLayout(orientation="horizontal", spacing=10)
		lower_middle_shell = BoxLayout(orientation="vertical", size_hint=(0.14, 1))
		lower_right_shell = BoxLayout(orientation="vertical", size_hint=(0.43, 1))
		lower_right_credit_shell = BoxLayout(orientation="horizontal")
		lower_right_buttons_shell = BoxLayout(orientation="horizontal", spacing=10)


		#Build upper game shell structure
		upper_game_shell.add_widget(upper_left_shell)
		upper_left_shell.add_widget(a_card_shell)
		a_card_shell.add_widget(a_card_title_shell)
		a_card_shell.add_widget(a_card_info_shell)
		upper_left_shell.add_widget(b_card_shell)
		b_card_shell.add_widget(b_card_title_shell)
		b_card_shell.add_widget(b_card_info_shell)
		upper_left_shell.add_widget(c_card_shell)
		c_card_shell.add_widget(c_card_title_shell)
		c_card_shell.add_widget(c_card_info_shell)
		upper_left_shell.add_widget(d_card_shell)
		d_card_shell.add_widget(d_card_title_shell)
		d_card_shell.add_widget(d_card_info_shell)
		upper_game_shell.add_widget(upper_right_shell)
		upper_right_shell.add_widget(card_buttons_shell)
		upper_right_shell.add_widget(keno_board_shell)
		keno_board_shell.add_widget(keno_board_top_shell)
		keno_board_shell.add_widget(keno_board_bottom_shell)

		#Build lower game shell structure
		lower_game_shell.add_widget(lower_left_shell)
		lower_left_shell.add_widget(lower_left_win_shell)
		lower_left_shell.add_widget(lower_left_buttons_shell)
		lower_game_shell.add_widget(lower_middle_shell)
		lower_game_shell.add_widget(lower_right_shell)
		lower_right_shell.add_widget(lower_right_credit_shell)
		lower_right_shell.add_widget(lower_right_buttons_shell)

		#Append to super gameshell
		self.add_widget(upper_game_shell)
		self.add_widget(lower_game_shell)

		self.info_marked_labels={}
		self.info_hits_labels={}
		self.info_bet_labels={}
		self.info_win_labels={}

		for i in range(0,4):
			self.info_marked_labels[i] = info_label("MARKED: ")
			self.info_hits_labels[i] = info_label("HITS: ")
			self.info_bet_labels[i] = info_label("BET: ")
			self.info_win_labels[i] = info_label("", gameYellow)

		a_card_title_shell.add_widget(Label(text='CARD',bold=True))
		a_card_title_shell.add_widget(Label(text='A',bold=True,font_size='25dp'))
		a_card_info_shell.add_widget(self.info_marked_labels[0])
		a_card_info_shell.add_widget(self.info_hits_labels[0])
		a_card_info_shell.add_widget(self.info_bet_labels[0])
		a_card_info_shell.add_widget(self.info_win_labels[0])
		#a_card_info_shell.add_widget(info_label("0 BALLS 0"))

		b_card_title_shell.add_widget(Label(text='CARD',bold=True))
		b_card_title_shell.add_widget(Label(text='B',bold=True,font_size='25dp'))
		b_card_info_shell.add_widget(self.info_marked_labels[1])
		b_card_info_shell.add_widget(self.info_hits_labels[1])
		b_card_info_shell.add_widget(self.info_bet_labels[1])
		b_card_info_shell.add_widget(self.info_win_labels[1])
		#b_card_info_shell.add_widget(info_label("0 BALLS 0"))

		c_card_title_shell.add_widget(Label(text='CARD',bold=True))
		c_card_title_shell.add_widget(Label(text='C',bold=True,font_size='25dp'))
		c_card_info_shell.add_widget(self.info_marked_labels[2])
		c_card_info_shell.add_widget(self.info_hits_labels[2])
		c_card_info_shell.add_widget(self.info_bet_labels[2])
		c_card_info_shell.add_widget(self.info_win_labels[2])
		#c_card_info_shell.add_widget(info_label("0 BALLS 0"))

		d_card_title_shell.add_widget(Label(text='CARD',bold=True))
		d_card_title_shell.add_widget(Label(text='D',bold=True,font_size='25dp'))
		d_card_info_shell.add_widget(self.info_marked_labels[3])
		d_card_info_shell.add_widget(self.info_hits_labels[3])
		d_card_info_shell.add_widget(self.info_bet_labels[3])
		d_card_info_shell.add_widget(self.info_win_labels[3])
		#d_card_info_shell.add_widget(info_label("0 BALLS 0"))


		self.a_card_button = Button(text='CARD A', background_normal='', background_color=gamePurple, bold=True)
		self.b_card_button = Button(text='CARD B', background_normal='', background_color=gameGreen, bold=True)
		self.c_card_button = Button(text='CARD C', background_normal='', background_color=gameOrange, bold=True)
		self.d_card_button = Button(text='CARD D', background_normal='', background_color=gamePink, bold=True)

		self.a_card_button.bind(on_press=partial(self.switchToCard, 0))
		self.b_card_button.bind(on_press=partial(self.switchToCard, 1))
		self.c_card_button.bind(on_press=partial(self.switchToCard, 2))
		self.d_card_button.bind(on_press=partial(self.switchToCard, 3))


		card_buttons_shell.add_widget(self.a_card_button)
		card_buttons_shell.add_widget(self.b_card_button)
		card_buttons_shell.add_widget(self.c_card_button)
		card_buttons_shell.add_widget(self.d_card_button)

		self.total_win_label = win_label(text='WIN ')
		lower_left_win_shell.add_widget(self.total_win_label)


		#BETUP BUTTON
		self.betup_button = Button(text='BET UP', color=(0,0,0,1), background_normal='', background_color=gameYellow, bold=True)
		self.betup_button.bind(on_press=self.betUpPressed)
		lower_left_buttons_shell.add_widget(self.betup_button)

		#lower_left_buttons_shell.add_widget(Button(text='HELP', color=(0,0,0,1), background_normal='', background_color=gameYellow, bold=True))

		#MORE GAMES BUTTON
		self.moregames_button = Button(text='MORE GAMES', color=(0,0,0,1), background_normal='', background_color=gameYellow, bold=True)
		lower_left_buttons_shell.add_widget(self.moregames_button)

		#SPEED BUTTON
		speedText='SPEED >' + '>'*self.speed
		self.speed_button = Button(text=speedText, color=(0,0,0,1), background_normal='', background_color=gameYellow, bold=True)
		self.speed_button.bind(on_press=self.speedPressed)
		lower_left_buttons_shell.add_widget(self.speed_button)


		self.total_bet_label = Label(text=(f'BET: {sum(self.bets)}'))
		lower_middle_shell.add_widget(self.total_bet_label)
		lower_middle_shell.add_widget(Label(text=f'{str(self.denom)[2:]}¢', font_size='34dp', color=gameRed, outline_color=gameYellow, outline_width=1, bold=True))


		self.credit_label = credit_label(text='CREDIT $'+f"{(self.credits*self.denom):.2f}")
		lower_right_credit_shell.add_widget(self.credit_label)

		#QUICK PICK BUTTON
		self.quickpick_button = Button(text='QUICK PICK', color=(0,0,0,1), background_normal='', background_color=gameYellow, bold=True)
		self.quickpick_button.bind(on_press=self.quickpickPressed)
		lower_right_buttons_shell.add_widget(self.quickpick_button)

		#lower_right_buttons_shell.add_widget(Button(text='CHANGE SPOTS', color=(0,0,0,1), background_normal='', background_color=gameYellow, bold=True))


		#AUTOPLAY BUTTON
		self.auto_button = Button(text='AUTOPLAY', color=(0,0,0,1), background_normal='', background_color=gameYellow, bold=True)
		self.auto_button.bind(on_press=self.autoPressed)
		lower_right_buttons_shell.add_widget(self.auto_button)

		#START BUTTON
		self.start_button = Button(text='START', color=(0,0,0,1), background_normal='', background_color=gameYellow, bold=True)
		self.start_button.bind(on_press=self.startPressed)
		lower_right_buttons_shell.add_widget(self.start_button)




		#BUILD SQUARES
		self.squares = {}

		for i in range(1,41):
			self.squares[i] = KenoButton(text=str(i), bold=True, background_color=gameBlue, color=gameYellow, outline_color=(0,0,0,0.5), outline_width=1, font_size='25dp', background_normal='', background_down='')
			self.squares[i].bind(on_press=partial(self.markSpot, i))
			keno_board_top_shell.add_widget(self.squares[i])
			self.squares[i+40] = KenoButton(text=str((i+40)), bold=True, background_color=gameBlue, color=gameYellow, outline_color=(0,0,0,0.5), outline_width=1, font_size='25dp', background_normal='', background_down='')
			self.squares[i+40].bind(on_press=partial(self.markSpot, i+40))
			keno_board_bottom_shell.add_widget(self.squares[i+40])



		#COLOR TITLES AND SHELLS
		self.a_info_bg_color, self.a_info_bg_rect = set_bg(a_card_shell, (1,1,1,0.1))
		set_bg(a_card_title_shell, gamePurple)
		self.b_info_bg_color, self.b_info_bg_rect = set_bg(b_card_shell, (1,1,1,0.1))
		set_bg(b_card_title_shell, gameGreen)
		self.c_info_bg_color, self.c_info_bg_rect = set_bg(c_card_shell, (1,1,1,0.1))
		set_bg(c_card_title_shell, gameOrange)
		self.d_info_bg_color, self.d_info_bg_rect = set_bg(d_card_shell, (1,1,1,0.1))
		set_bg(d_card_title_shell, gamePink)
		set_bg(keno_board_top_shell, gameYellow)
		set_bg(keno_board_bottom_shell, gameYellow)

		###SET LEDS START
		self.updateLeds()



	#---GAME FUNCTIONS---

	def buttonPushed(self, butNum):
		match butNum:
			case 0:
				Clock.schedule_once(lambda dt: self.increaseBet(), 0)
			case 1:
				print("1")
			case 2:
				Clock.schedule_once(lambda dt: self.cycleSpeed(), 0)
			case 3:
				print("3")
			case 4:
				Clock.schedule_once(lambda dt: self.quickpickNums(), 0)
			case 5:
				Clock.schedule_once(lambda dt: self.toggleAuto(), 0)
			case 6:
				Clock.schedule_once(lambda dt: self.startSpin(), 0)
			case _:
				print("defaulted")

	def speedPressed(self,instance):
		self.cycleSpeed()

	def cycleSpeed(self):
		if self.spinning:
			return
		if self.speed>=2:
			self.speed=0
			self.speed_button.text='SPEED >'
			return
		self.speed+=1
		self.speed_button.text='SPEED >' + '>'*self.speed

	def playBoop(self,hit):
		if hit:
			self.boop_high.play()
		else:
			self.boop_low.play()

	def resetBoard(self):
		for square in self.squares.values():
			square.background_color=gameBlue
		self.drawnNums = ()


	def greyButtons(self):
		self.start_button.background_color=gameGrey
		self.speed_button.background_color=gameGrey
		self.betup_button.background_color=gameGrey
		self.moregames_button.background_color=gameGrey
		self.quickpick_button.background_color=gameGrey

		self.start_button.text=''
		self.speed_button.text=''
		self.betup_button.text=''
		self.moregames_button.text=''
		self.quickpick_button.text=''

		self.updateLeds()

	def recolorButtons(self):
		self.start_button.background_color=gameYellow
		self.speed_button.background_color=gameYellow
		self.betup_button.background_color=gameYellow
		self.moregames_button.background_color=gameYellow
		self.quickpick_button.background_color=gameYellow

		self.start_button.text='START'
		self.speed_button.text='SPEED >'+'>'*self.speed
		self.betup_button.text='BET UP'
		self.moregames_button.text='MORE GAMES'
		self.quickpick_button.text='QUICK PICK'

		self.updateLeds()

	def updateLeds(self):
		if self.spinning:
			for i, led in enumerate(self.leds):
				if i != 5:
					led.off()
				else:
					led.on()
			return
		if self.validSpin():
			self.leds[6].on()
		else:
			self.leds[6].off()
		for i in range(6):
			self.leds[i].on()


	def turnInfoBoxYellow(self, card):
		match card:
			case 0:
				self.a_info_bg_color.rgba = gameYellow
				self.info_marked_labels[0].color = (0,0,0,1)
				self.info_hits_labels[0].color = (0,0,0,1)
				self.info_bet_labels[0].color = (0,0,0,1)
				self.info_win_labels[0].color = (gameRed)
			case 1:
				self.b_info_bg_color.rgba = gameYellow
				self.info_marked_labels[1].color = (0,0,0,1)
				self.info_hits_labels[1].color = (0,0,0,1)
				self.info_bet_labels[1].color = (0,0,0,1)
				self.info_win_labels[1].color = (gameRed)
			case 2:
				self.c_info_bg_color.rgba = gameYellow
				self.info_marked_labels[2].color = (0,0,0,1)
				self.info_hits_labels[2].color = (0,0,0,1)
				self.info_bet_labels[2].color = (0,0,0,1)
				self.info_win_labels[2].color = (gameRed)
			case 3:
				self.d_info_bg_color.rgba = gameYellow
				self.info_marked_labels[3].color = (0,0,0,1)
				self.info_hits_labels[3].color = (0,0,0,1)
				self.info_bet_labels[3].color = (0,0,0,1)
				self.info_win_labels[3].color = (gameRed)

	def resetInfoBoxes(self):
		self.a_info_bg_color.rgba = (1,1,1,0.1)
		self.b_info_bg_color.rgba = (1,1,1,0.1)
		self.c_info_bg_color.rgba = (1,1,1,0.1)
		self.d_info_bg_color.rgba = (1,1,1,0.1)
		for i in range(0,4):
			self.info_marked_labels[i].color = (1,1,1,1)
			self.info_hits_labels[i].color = (1,1,1,1)
			self.info_bet_labels[i].color = (1,1,1,1)
			self.info_win_labels[i].color = (gameYellow)

	def calculatePaySpeed(self, win):
		k = 0.31
		p = 0.40
		dt = k * (win ** (p-1.0))
		return max(0.001, min(dt, 0.08))

	def calculateWin(self, card):
		_win = (self.pay_table[len(self.marked_spots[card])][self.hit_counts[card]])*self.bets[card]
		if _win > 0:
			self.info_win_labels[card].text="WIN: "+str(_win)
			if (_win/self.bets[card]) >= 91:
				self.turnInfoBoxYellow(card)
		self.wins[card] = _win

	def payoutWin(self,dt):
		if sum(self.wins) < 0 or self.pay_idx >= sum(self.wins):
			self.spinning=False
			self.ready=True
			self.paying=False
			self.credits += self.pay_idx

			#IF AUTO PLAY IS ON: RESTART THE LOOP
			if self.auto_on: self.startSpin()
			else: self.recolorButtons()

			return

		self.pay_idx += 1

		self.total_win_label.text = "WIN "+str(self.pay_idx)

		self.credit_label.text='CREDIT $'+f"{((self.credits+self.pay_idx)*self.denom):.2f}"

		Clock.schedule_once(self.payoutWin, self.pay_speed)

	def drawTillDone(self,dt):
		_did_hit=False
		if self.draw_idx >= len(self.drawnNums):
			self.paying=True
			if sum(self.wins) > 0: self.pay_speed=self.calculatePaySpeed(sum(self.wins))
			self.pay_idx=0
			self.payoutWin(0)
			return
		self.squares[self.drawnNums[self.draw_idx]].background_color=gameRed
		for i, card in enumerate(self.marked_spots):
			if self.drawnNums[self.draw_idx] in card:
				self.hit_counts[i] += 1
				self.info_hits_labels[i].text = "HITS: "+str(self.hit_counts[i])
				self.calculateWin(i)
				_did_hit=True
		self.playBoop(_did_hit)
		self.draw_idx += 1
		Clock.schedule_once(self.drawTillDone, self.speed_times[self.speed])

	def validSpin(self):
		if sum(self.bets) <= 0 or self.credits < sum(self.bets):
			return False
		for i in range(0,4):
			if self.bets[i] > 0 and len(self.marked_spots[i]) <= 1:
				return False
		return True

	def autoPressed(self,instance):
		self.toggleAuto()

	def toggleAuto(self):
		if not self.auto_on:
			self.auto_button.text='STOP AUTO'
			if not self.spinning:
				self.startSpin()
		else: self.auto_button.text='AUTOPLAY'
		self.auto_on = not self.auto_on

	def startPressed(self,instance):
		self.startSpin()

	def startSpin(self):

		if self.spinning:
			self.speed_times[self.speed] = 0.01
			if self.auto_on:
				self.auto_on=False
				self.auto_button.text='AUTOPLAY'
		if self.paying:
			self.pay_speed=0.0001
		if not self.ready:
			return
		if not self.validSpin():
			self.recolorButtons()
			self.auto_on=False
			self.auto_button.text='AUTOPLAY'
			return

		self.credits -= sum(self.bets)
		self.credit_label.text='CREDIT $'+f"{(self.credits*self.denom):.2f}"

		self.ready=False

		self.resetBoard()
		self.resetInfoBoxes()
		self.hit_counts=[0,0,0,0]
		self.updateInfoHits()
		self.wins=[0,0,0,0]
		self.updateInfoWin()
		self.total_win_label.text = "WIN "

		self.current_card=4
		self.showCardsMarkedSpots(self.current_card)

		for i in range(0,len(self.speed_times)):
			self.speed_times[i]=self.LOCKED_speed_times[i]
		self.spinning=True
		self.greyButtons()
		self.draw_idx=0
		self.drawnNums=random.sample(range(1, 81),20)
		self.drawTillDone(0)

	def updateInfoMarked(self):
		for i, label in enumerate(self.info_marked_labels.values()):
			label.text="MARKED: "+str(len(self.marked_spots[i]))

	def updateInfoHits(self):
		for i, label in enumerate(self.info_hits_labels.values()):
			label.text="HITS: "+str(self.hit_counts[i])

	def updateInfoBet(self):
		for i, label in enumerate(self.info_bet_labels.values()):
			label.text="BETS: "+str(self.bets[i])

	def updateInfoWin(self):
		for i, label in enumerate(self.info_win_labels.values()):
			label.text=""

	def switchToCard(self, card, instance):
		if self.spinning: return
		if self.current_card==card:
			self.current_card=4
			self.updateInfoMarked()
		else: self.current_card=card
		for square in self.squares.values():
			if int(square.text) not in self.drawnNums:
				square.background_color=self.getColorFromCard(self.current_card)
			else: square.background_color=gameRed
		self.showCardsMarkedSpots(self.current_card)

	def getLetterFromCard(self, num):
		match num:
			case 0:
				return 'A'
			case 1:
				return 'B'
			case 2:
				return 'C'
			case 3:
				return 'D'
			case 4:
				return 'ALL'
			case _:
				return 'ERROR'

	def getColorFromCard(self,num):
		match num:
			case 0:
				return gamePurple
			case 1:
				return gameGreen
			case 2:
				return gameOrange
			case 3:
				return gamePink
			case 4:
				return gameBlue
			case _:
				return gameGrey


	def markSpot(self, num, instance):
		if self.current_card==4: return
		if num in self.marked_spots[self.current_card]:
			self.marked_spots[self.current_card].remove(num)
			self.squares[num].is_marked=False
			self.squares[num].marked_text=''
		elif len(self.marked_spots[self.current_card]) <= 9:
			self.marked_spots[self.current_card].append(num)
			self.squares[num].is_marked=True
			self.squares[num].marked_text=self.getLetterFromCard(self.current_card)
			self.squares[num].marked_text_color=self.getColorFromCard(self.current_card)
		self.updateInfoMarked()
		self.updateLeds()


	def showCardsMarkedSpots(self, card):
		if card < 4:
			_cur_let=self.getLetterFromCard(card)
			_cur_col=self.getColorFromCard(card)
			for square in self.squares.values():
				if int(square.text) in self.marked_spots[card]:
					square.is_marked=True
					square.marked_text=_cur_let
					square.marked_text_color=_cur_col
				else:
					square.is_marked=False
		else:
			for square in self.squares.values():
				square.is_marked=False
			for i, c in enumerate(self.marked_spots):
				for n in c:
					if self.bets[i] > 0:
						if self.squares[n].is_marked:
							self.squares[n].marked_text='*'
							self.squares[n].marked_text_color=(0,0,0,1)
						else:
							self.squares[n].is_marked=True
							self.squares[n].marked_text=self.getLetterFromCard(i)
							self.squares[n].marked_text_color=self.getColorFromCard(i)

	def betUpPressed(self,instance):
		self.increaseBet()

	def increaseBet(self):
		if self.spinning: return
		if self.current_card < 4:
			if self.bets[self.current_card] >= self.max_bet:
				self.bets[self.current_card]=0
			else:
				self.bets[self.current_card]+=1
			self.info_bet_labels[self.current_card].text="BET: "+str(self.bets[self.current_card])
		elif sum(self.bets) == self.max_bet*4:
			self.bets=[0,0,0,0]
			self.updateInfoBet()
			self.showCardsMarkedSpots(4)
		else:
			_target = self.bets.index(min(self.bets))
			self.bets[_target]+=1
			self.info_bet_labels[_target].text="BET: "+str(self.bets[_target])
			self.showCardsMarkedSpots(4)
		self.total_bet_label.text="BET: "+str(sum(self.bets))
		self.updateLeds()

	def quickpickPressed(self,instance):
		self.quickpickNums()

	def quickpickNums(self):
		if self.current_card == 4:
			return
		cur_count = 8
		if len(self.marked_spots[self.current_card]) > 1:
			cur_count = len(self.marked_spots[self.current_card])
		self.marked_spots[self.current_card].clear()

		rand_pick = random.sample(range(1, 81),cur_count)
		self.marked_spots[self.current_card] = rand_pick
		self.showCardsMarkedSpots(self.current_card)

class MyApp(App):

	def build(self):
		return Fourcard()

if __name__ == '__main__':
	MyApp().run()

