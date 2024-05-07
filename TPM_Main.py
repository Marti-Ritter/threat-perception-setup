import sys
import pygame
import multiprocessing
import screeninfo
import pygameMenu
import random as rdm
import os
import json
import datetime
from dateutil import parser
import time
import pygame.gfxdraw as gfxdraw
import math
from collections import deque
import TPM_Utility
import TPM_Recorder
import TPM_Statistics
import pyautogui

# Importing Matplotlib for performance-graph and statistics window
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.backends.backend_agg as agg

# Importing Fontmanager for getting the proper fonts
import matplotlib.font_manager as fontman

# -----------------------------------------------------------------------------
# Colors
# -----------------------------------------------------------------------------
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
MENU_BACKGROUND_COLOR = (228, 55, 36)
ACTIVE_COLOR = tuple(map(sum, zip(MENU_BACKGROUND_COLOR, (+10, +10, +10))))
COLOR_BACKGROUND = (128, 0, 128)


# -----------------------------------------------------------------------------
# Classes
# -----------------------------------------------------------------------------
class ExperimentScreen:
    def __init__(self, parent, size, position, marker_distribution, marker_height,
                 image_location, font, background_color=(0, 0, 0), mirrored=True):
        assert isinstance(parent, pygame.Surface), \
            'Parent must be a Pygame surface.'
        assert isinstance(size, tuple) and len(size) == 2 and all(i > 0 for i in size), \
            'Size must be a int-tuple of length 2 with all values greater than 0.'
        assert isinstance(position, tuple) and len(position) == 2, \
            'Position must be a int-tuple of length 2.'
        assert isinstance(background_color, tuple) and len(background_color) == 3 and \
               all(0 <= i < 256 for i in background_color), \
            'The background color must be a int-tuple of length 3 (RGB).'
        assert isinstance(marker_distribution, tuple) and len(marker_distribution) == 3 and \
               all(i > 0 for i in marker_distribution), \
            'The marker distribution must be a int-tuple of length 3 (left of screen, on screen, right of screen).'
        assert isinstance(marker_height, int) and marker_height > 0, \
            'The marker height must be an integer above 0.'
        assert isinstance(image_location, list) and len(image_location) > 0 and \
               all(isinstance(location, str) for location in image_location), \
            'The image location must be a list of strings, which show the possible images for the markers.'
        assert isinstance(mirrored, bool), \
            'The mirrored flag must be a boolean deciding whether the markers are mirrored at the middle of the screen.'

        self.parent = parent
        self.surface = pygame.Surface(size)
        self.surface.fill(COLOR_BACKGROUND)
        experiment_text = "Experiment"
        experiment_render = font.render(experiment_text, 0, (255, 255, 255))
        self.surface.blit(experiment_render,
                          ((size[0] - experiment_render.get_width()) / 2,
                           (size[1] - experiment_render.get_height()) / 2))

        self.rectangle = self.surface.get_rect().move(position)
        self.background_color = background_color
        self.marker_height = marker_height
        self.image_location = image_location
        self.mirrored = mirrored
        self.markers = deque(maxlen=sum(marker_distribution))

        _surf = [None] * sum(marker_distribution)
        _rect = [None] * sum(marker_distribution)

        for i in range(sum(marker_distribution)):
            loaded_image = pygame.image.load(image_location[rdm.randint(0, len(image_location) - 1)])
            zoom_factor = marker_height / loaded_image.get_height()
            if self.mirrored:
                _surf[i] = [pygame.transform.rotozoom(loaded_image, 0, zoom_factor),
                            pygame.transform.flip(pygame.transform.rotozoom(loaded_image, 180, zoom_factor),
                                                  True, False)]
            else:
                _surf[i] = pygame.transform.rotozoom(loaded_image, 0, zoom_factor)

        self.location_pointer = _surf[marker_distribution[0]][0].get_width() / 2
        self.space = parent.get_width() / marker_distribution[1]
        self.left_spawn = -(marker_distribution[0] * self.space)
        self.right_spawn = parent.get_width() + marker_distribution[2] * self.space

        for i in range(sum(marker_distribution)):
            if self.mirrored:
                _rect[i] = [_surf[i][0].get_rect(), _surf[i][1].get_rect()]
                _rect[i][0].center = [(-marker_distribution[0] + i) * self.space
                                      + self.location_pointer, parent.get_height() * 1 / 4]
                _rect[i][1].center = [(-marker_distribution[0] + i) * self.space
                                      + self.location_pointer, parent.get_height() * 3 / 4]
            else:
                _rect[i] = _surf[i][0].get_rect()
                _rect[i].center = [(-marker_distribution[0] + i) * self.space
                                   + self.location_pointer, parent.get_height() * 2 / 4]

            wobble_x_abs = int(self.space / 3)
            wobble_x_random = rdm.randint(-wobble_x_abs, wobble_x_abs)

            if self.mirrored:
                wobble_y_abs = int(parent.get_height() / 4 - _rect[i][0].height / 2)
                wobble_y_random = rdm.randint(-wobble_y_abs, wobble_y_abs)
                _rect[i] = [_rect[i][0].move(wobble_x_random, wobble_y_random),
                            _rect[i][1].move(wobble_x_random, -wobble_y_random)]
                self.markers.append([[_surf[i][0], _rect[i][0]], [_surf[i][1], _rect[i][1]]])

            else:
                wobble_y_abs = int((parent.get_width() / 2))
                wobble_y_random = rdm.randint(-wobble_y_abs, wobble_y_abs)
                _rect[i] = _rect[i].move(wobble_x_random, wobble_y_random)
                self.markers.append([_surf[i], _rect[i]])
        print("init")
        self.move(0)

    def move(self, delta):
        self.surface.fill(self.background_color)
        self.location_pointer += delta

        if self.location_pointer < 0 or self.location_pointer > self.space:
            if self.location_pointer < 0:
                spawn = self.right_spawn
            else:
                spawn = self.left_spawn

            loaded_image = pygame.image.load(self.image_location[rdm.randint(0, len(IMAGE_LIST) - 1)])
            zoom_factor = self.marker_height / loaded_image.get_height()
            if self.mirrored:
                _surf = [pygame.transform.rotozoom(loaded_image, 0, zoom_factor),
                         pygame.transform.flip(pygame.transform.rotozoom(loaded_image, 180, zoom_factor),
                                               True, False)]

                _rect = [_surf[0].get_rect(),
                         _surf[1].get_rect()]
                _rect[0].center = [spawn, self.parent.get_height() * 1 / 4]
                _rect[1].center = [spawn, self.parent.get_height() * 3 / 4]
                wobble_y_abs = int(self.parent.get_height() / 4 - _rect[0].height / 2)
                wobble_y_random = rdm.randint(-wobble_y_abs, wobble_y_abs)
            else:
                _surf = pygame.transform.rotozoom(loaded_image, 0, zoom_factor)
                _rect = _surf.get_rect()
                _rect.center = [spawn, self.parent.get_height() * 2 / 4]
                wobble_y_abs = int(self.parent.get_height() / 2)
                wobble_y_random = rdm.randint(-wobble_y_abs, wobble_y_abs)

            wobble_x_abs = int(self.space / 3)
            wobble_x_random = rdm.randint(-wobble_x_abs, wobble_x_abs)

            if self.mirrored:
                _rect = (_rect[0].move(wobble_x_random, wobble_y_random),
                         _rect[1].move(wobble_x_random, -wobble_y_random))
                new_marker = [[_surf[0], _rect[0]], [_surf[1], _rect[1]]]
            else:
                _rect = _rect.move(wobble_x_random, wobble_y_random)
                new_marker = [_surf, _rect]

            if self.location_pointer < 0:
                self.markers.append(new_marker)
                print("append right")
            else:
                self.markers.appendleft(new_marker)
                print("append left")

            self.location_pointer = self.location_pointer % self.space

        for i in range(0, len(self.markers)):
            if self.mirrored:
                self.markers[i][0][1] = self.markers[i][0][1].move(delta, 0)
                self.markers[i][1][1] = self.markers[i][1][1].move(delta, 0)
                self.surface.blit(*self.markers[i][0])
                self.surface.blit(*self.markers[i][1])
            else:
                self.markers[i][1] = self.markers[i][1].move(delta, 0)
                self.surface.blit(*self.markers[i])

    def blit_to_parent(self):
        self.parent.blit(self.surface, self.rectangle)


# -----------------------------------------------------------------------------
# Global variables
# -----------------------------------------------------------------------------
ABOUT = ['Uncertainty Project',
         'Arduino Programming and Hardware by',
         'Ronny Bergmann',
         'Raspberry Pi Programming and',
         'User Interface Structure by Marti Ritter',
         pygameMenu.locals.TEXT_NEWLINE,
         'Email:',
         'Ronny Bergmann: Ronny.Bergmann91@web.de',
         'Marti Ritter: Marti.R@web.de',
         pygameMenu.locals.TEXT_NEWLINE,
         'Pygame-Menu Module',
         'pygameMenu {0}'.format(pygameMenu.__version__),
         'Author: @{0}'.format(pygameMenu.__author__)]
MOUSE_INFO = []
CURRENT_MOUSE = None
MOUSE_NR = None
RAT_INFO = []
CURRENT_RAT = None
RAT_NR = None
FPS = 60.0

SCREEN = None

WINDOW_SIZE = (0, 0)  # If set to (0,0) pygame automatically determines the size
MENU_SIZE = (640, 480)

FONT_NAME = None
MESSAGE_TIMERS = {
    "Mouse added.": None,
    "Mouse removed.": None,
    "Rat added.": None,
    "Rat removed.": None,
    "Config saved.": None,
    "Pixel/Centimeter calibrated.": None,
    "No mouse found.": None,
    "No rat found.": None,
    "Experiment finished.": None,
    "Experiment ended.": None
}

VIRTUAL_EXPERIMENT = False

CONFIG = None
RESULTS = None
clock = None
main_menu = None

p_cm_input = None  # Location where the p_cm_ratio gets updated in the menu

MAIN_MENUBAR = None  # Helps drawing the performance plot into the menu
EXPERIMENT_MENUBAR = None
PAIRING_MENUBAR = None
HARDWARE_MENUBAR = None

IMAGE_LIST = ["Ball.gif",
              "Cylinder.gif",
              "RoundPyramid.gif",
              "RoundRing.gif",
              "TiltedBarRight.gif",
              "TiltedBarLeft.gif",
              "Cube.gif"]

hardware_descriptions = ["This pin will control the disk position. It can only be set to the 2 PWM0-pins. PWM0 will"
                         " send a 500Hz signal with pulses between 200µs and 1200µs, which will be translated to a "
                         "relative position (0-100).",
                         "This pin will control the tube position. It can only be set to the single PWM1-pin. PWM1 will"
                         " send a 500Hz signal with pulses between 200µs and 1200µs, which will be translated to a "
                         "relative position (0-100).",
                         "This pin will receive the licking signal of the mouse, when the tube has reached the maximum "
                         "position. When the mouse licks, reward will be dispensed during the experiment. The input "
                         "signal must be 3.3VDC.",
                         "This pin will send a logical (0/1) signal to dispense the reward for the mouse. The output "
                         "signal will be 3.3VDC.",
                         "This pin will receive the licking signal of the rat throughout the experiment. The position "
                         "of the rat is important during the experiment and should be close to the mouse. The input "
                         "signal must be 3.3VDC.",
                         "This pin will send a logical (0/1) signal to dispense the reward for the rat. The output "
                         "signal will be 3.3VDC.",
                         "Click this to return to the previous menu. "
                         ]

special_pins = (('1', "3.3 VDC"), ('2', "5.0 VDC"), ('3', "ADC SDA"), ('4', "Ground"), ('5', "ADC SCL"),
                ('6', "Ground"), ('9', "Ground"), ('14', "Ground"), ('17', "3.3 VDC"), ('20', "Ground"),
                ('25', "Ground"), ('27', "EEPROM SDA"), ('28', "EEPROM SCL"), ('30', "Ground"), ('34', "Ground"),
                ('39', "Ground"))

pin_positions = ((422, 85), (441, 85),
                 (422, 104), (441, 104),
                 (422, 124), (441, 124),
                 (422, 143), (441, 143),
                 (422, 163), (441, 163),
                 (422, 182), (441, 182),
                 (422, 202), (441, 202),
                 (422, 221), (441, 221),
                 (422, 241), (441, 241),
                 (422, 260), (441, 260),
                 (422, 280), (441, 280),
                 (422, 299), (441, 299),
                 (422, 319), (441, 319),
                 (422, 338), (441, 338),
                 (422, 358), (441, 358),
                 (422, 377), (441, 377),
                 (422, 396), (441, 396),
                 (422, 416), (441, 416),
                 (422, 436), (441, 436),
                 (422, 455), (441, 455))


# -----------------------------------------------------------------------------
# Methods
# -----------------------------------------------------------------------------
def _from_rgb(rgb):
    """translates an rgb tuple of int to a tkinter friendly color code
    """
    return "#%02x%02x%02x" % rgb


# from cristiao2lopes on stackoverflow
def find_font_file(query):
    matches = list(filter(lambda path: query.casefold() in os.path.basename(path).casefold(),
                          fontman.findSystemFonts()))
    matches = sorted(matches, key=lambda s: s.casefold())
    return matches


def plot_performance(x, y):
    ax = plt.gca()
    for l in ax.get_lines():
        l.remove()
    ax.plot(x, y, color='black', linewidth=0.75)
    plt.xticks(x)
    canvas = agg.FigureCanvasAgg(plt.gcf())
    canvas.draw()
    renderer = canvas.get_renderer()
    raw_data = renderer.tostring_rgb()
    size = canvas.get_width_height()
    if not main_menu._actual.get_title() == 'Select Animals':
        ax.set_title("Pairing Duration over time [s]")
        ax.set_ylim(0, max(y))
    else:
        ax.set_title("Performance over time [%]")
        ax.set_ylim(0, 100)
    return pygame.image.fromstring(raw_data, size, "RGB")


def main_background():
    """
    Function used by menus, draw on background while menu is active.
    :return: None
    """
    SCREEN.fill(COLOR_BACKGROUND)

    if main_menu._actual.get_title() == 'Select Animals':
        back_rect = pygame.Rect((0, 0), (int(MENU_SIZE[0] * 0.8), int(MENU_SIZE[1] * 1.25)))
        back_rect.center = (WINDOW_SIZE[0] / 2, WINDOW_SIZE[1] / 2)
        pygame.draw.rect(SCREEN, MENU_BACKGROUND_COLOR, back_rect)
        gfxdraw.filled_polygon(SCREEN, EXPERIMENT_MENUBAR._polygon_pos, MAIN_MENUBAR._font_color)

        if len(CONFIG["mice"]) > 0 and CONFIG["mice"][CURRENT_MOUSE]["performance"].keys():
            performance = [CONFIG["mice"][CURRENT_MOUSE]["performance"][date] for date
                           in CONFIG["mice"][CURRENT_MOUSE]["performance"]]
            dates = [parser.parse(date, dayfirst=True) for date in CONFIG["mice"][CURRENT_MOUSE]["performance"]]
            if not all(date < datetime.datetime.today() - datetime.timedelta(days=14) for date in dates):
                surface = plot_performance(dates, performance)
                plot_rect = surface.get_rect()
                plot_rect.center = back_rect.center
                plot_rect.centery = plot_rect.centery + 40
                SCREEN.blit(surface, plot_rect)

    elif main_menu._actual.get_title() == 'Select Mouse':
        back_rect = pygame.Rect((0, 0), (int(MENU_SIZE[0] * 0.8), int(MENU_SIZE[1] * 1.25)))
        back_rect.center = (WINDOW_SIZE[0] / 2, WINDOW_SIZE[1] / 2)
        pygame.draw.rect(SCREEN, MENU_BACKGROUND_COLOR, back_rect)
        gfxdraw.filled_polygon(SCREEN, PAIRING_MENUBAR._polygon_pos, MAIN_MENUBAR._font_color)

        if len(CONFIG["mice"]) > 0 and CONFIG["mice"][CURRENT_MOUSE]["pairing_duration"].keys():
            performance = [CONFIG["mice"][CURRENT_MOUSE]["pairing_duration"][date] for date
                           in CONFIG["mice"][CURRENT_MOUSE]["pairing_duration"]]
            dates = [parser.parse(date, dayfirst=True) for date in CONFIG["mice"][CURRENT_MOUSE]["pairing_duration"]]
            surface = plot_performance(dates, performance)
            plot_rect = surface.get_rect()
            plot_rect.center = back_rect.center
            plot_rect.centery = plot_rect.centery + 40
            SCREEN.blit(surface, plot_rect)

    elif main_menu._actual.get_title() == 'Select Rat':
        back_rect = pygame.Rect((0, 0), (int(MENU_SIZE[0] * 0.8), int(MENU_SIZE[1] * 1.25)))
        back_rect.center = (WINDOW_SIZE[0] / 2, WINDOW_SIZE[1] / 2)
        pygame.draw.rect(SCREEN, MENU_BACKGROUND_COLOR, back_rect)
        gfxdraw.filled_polygon(SCREEN, PAIRING_MENUBAR._polygon_pos, MAIN_MENUBAR._font_color)

        if len(CONFIG["mice"]) > 0 and CONFIG["rats"][CURRENT_RAT]["pairing_duration"].keys():
            performance = [CONFIG["rats"][CURRENT_RAT]["pairing_duration"][date] for date
                           in CONFIG["rats"][CURRENT_RAT]["pairing_duration"]]
            dates = [parser.parse(date) for date in CONFIG["rats"][CURRENT_RAT]["pairing_duration"]]
            surface = plot_performance(dates, performance)
            plot_rect = surface.get_rect()
            plot_rect.center = back_rect.center
            plot_rect.centery = plot_rect.centery + 40
            SCREEN.blit(surface, plot_rect)

    elif main_menu._actual.get_title() == 'Hardware Settings':
        back_rect = pygame.Rect((0, 0), (int(MENU_SIZE[0] * 1.5), int(MENU_SIZE[1] * 1.55)))
        back_rect.midtop = (WINDOW_SIZE[0] / 2, (WINDOW_SIZE[1] * 1.2) / 2 - MENU_SIZE[1])
        pygame.draw.rect(SCREEN, MENU_BACKGROUND_COLOR, back_rect)
        gfxdraw.filled_polygon(SCREEN, HARDWARE_MENUBAR._polygon_pos, MAIN_MENUBAR._font_color)
        text_rect = pygame.Rect((0, 0), (int(MENU_SIZE[0] * 1.05), int(MENU_SIZE[1] * 0.8)))
        text_rect = text_rect.move(WINDOW_SIZE[0] * 0.13, WINDOW_SIZE[1] * 0.12)
        text_font = pygame.font.SysFont(FONT_NAME, 30, bold=False)
        annotation_font = pygame.font.SysFont(FONT_NAME, 15, bold=True)
        blit_text_in_area(SCREEN, text_rect, hardware_descriptions[main_menu._actual._index], text_font)
        pinout_surface = pygame.image.load('RaspberryPi3bplus.png')
        image_width, image_height = pinout_surface.get_size()
        annotation_surface = pygame.Surface((2 * image_width, image_height), pygame.SRCALPHA, 32)
        annotation_surface = annotation_surface.convert_alpha()

        for pin in special_pins:
            pin_number = int(pin[0])
            if pin_number % 2 != 0:
                pygame.draw.line(annotation_surface, COLOR_BLACK,
                                 (int(0.5 * image_width) + pin_positions[pin_number - 1][0],
                                  pin_positions[pin_number - 1][1]),
                                 (int(0.5 * image_width) + pin_positions[pin_number - 1][0] - 75,
                                  pin_positions[pin_number - 1][1]))
                word_surface = annotation_font.render(pin[1], 0, COLOR_BLACK)
                word_rect = word_surface.get_rect()
                word_rect.midright = (int(0.5 * image_width) + pin_positions[pin_number - 1][0] - 80,
                                      pin_positions[pin_number - 1][1])
                annotation_surface.blit(word_surface, word_rect)

            else:
                pygame.draw.line(annotation_surface, COLOR_BLACK,
                                 (int(0.5 * image_width) + pin_positions[pin_number - 1][0],
                                  pin_positions[pin_number - 1][1]),
                                 (int(0.5 * image_width) + pin_positions[pin_number - 1][0] + 30,
                                  pin_positions[pin_number - 1][1]))
                word_surface = annotation_font.render(pin[1], 0, COLOR_BLACK)
                word_rect = word_surface.get_rect()
                word_rect.midleft = (int(0.5 * image_width) + pin_positions[pin_number - 1][0] + 35,
                                     pin_positions[pin_number - 1][1])
                annotation_surface.blit(word_surface, word_rect)

        input_data = main_menu._actual.get_input_data()
        for input_key in input_data.keys():
            pin_number = int(input_data[input_key][0])
            corresponding_widget = main_menu._actual.get_widget(input_key)
            if corresponding_widget.selected:
                annotation_color = COLOR_WHITE
            else:
                annotation_color = COLOR_BLACK
            if pin_number % 2 != 0:
                pygame.draw.line(annotation_surface, annotation_color,
                                 (int(0.5 * image_width) + pin_positions[pin_number - 1][0],
                                  pin_positions[pin_number - 1][1]),
                                 (int(0.5 * image_width) + pin_positions[pin_number - 1][0] - 75,
                                  pin_positions[pin_number - 1][1]))
                word_surface = annotation_font.render(corresponding_widget._label.strip(': '),
                                                      0, annotation_color)
                word_rect = word_surface.get_rect()
                word_rect.midright = (int(0.5 * image_width) + pin_positions[pin_number - 1][0] - 80,
                                      pin_positions[pin_number - 1][1])
                annotation_surface.blit(word_surface, word_rect)

            else:
                pygame.draw.line(annotation_surface, annotation_color,
                                 (int(0.5 * image_width) + pin_positions[pin_number - 1][0],
                                  pin_positions[pin_number - 1][1]),
                                 (int(0.5 * image_width) + pin_positions[pin_number - 1][0] + 30,
                                  pin_positions[pin_number - 1][1]))
                word_surface = annotation_font.render(corresponding_widget._label.strip(': '),
                                                      0, annotation_color)
                word_rect = word_surface.get_rect()
                word_rect.midleft = (int(0.5 * image_width) + pin_positions[pin_number - 1][0] + 35,
                                     pin_positions[pin_number - 1][1])
                annotation_surface.blit(word_surface, word_rect)

        annotation_surface = pygame.transform.rotozoom(annotation_surface, 0, 1.3)
        pinout_surface = pygame.transform.rotozoom(pinout_surface, 0, 1.3)
        pinout_rectangle = pinout_surface.get_rect().move(WINDOW_SIZE[0] * 0.335, WINDOW_SIZE[1] * 0.17)
        annotation_rectangle = annotation_surface.get_rect()
        annotation_rectangle.center = pinout_rectangle.center
        SCREEN.blit(pinout_surface, pinout_rectangle)
        SCREEN.blit(annotation_surface, annotation_rectangle)

    global MESSAGE_TIMERS
    if any(MESSAGE_TIMERS.values()):
        font = pygame.font.SysFont(FONT_NAME, 30, bold=True)
        for Message in MESSAGE_TIMERS.keys():
            if MESSAGE_TIMERS[Message]:
                if MESSAGE_TIMERS[Message] > time.time():
                    blit_text(SCREEN, Message, (2 * font.get_height(), WINDOW_SIZE[1] - 2 * font.get_height()), font)
                else:
                    MESSAGE_TIMERS[Message] = None


def blit_text(surface, text, pos, font, color=pygame.Color('black')):  # Thanks StackOverflow (@Ted Klein Bergman)
    words = [word.split(' ') for word in text.splitlines()]  # 2D array where each row is a list of words.
    space = font.size(' ')[0]  # The width of a space.
    max_width, max_height = surface.get_size()
    x, y = pos
    for line in words:
        for word in line:
            word_surface = font.render(word, 0, color)
            word_width, word_height = word_surface.get_size()
            if x + word_width >= max_width:
                x = pos[0]  # Reset the x.
                y += word_height  # Start on new row.
            surface.blit(word_surface, (x, y))
            x += word_width + space
        x = pos[0]  # Reset the x.
        y += word_height  # Start on new row.


def blit_text_in_area(surface, area, text, font, color=pygame.Color('black')):  # Adapted from above
    words = [word.split(' ') for word in text.splitlines()]  # 2D array where each row is a list of words.
    space = font.size(' ')[0]  # The width of a space.
    max_width, max_height = area.size
    x, y = area.topleft
    for line in words:
        for word in line:
            word_surface = font.render(word, 0, color)
            word_width, word_height = word_surface.get_size()
            if x + word_width >= max_width:
                x = area.left  # Reset the x.
                y += word_height  # Start on new row.
            surface.blit(word_surface, (area.left + x, area.top + y))
            x += word_width + space
        x = area.left  # Reset the x.
        y += word_height  # Start on new row.


def save_results():
    with open('results.json', 'w') as outfile:
        json.dump(RESULTS, outfile, indent=4, default=str)


# -------------------------------------------------------------------------
# Loops
# -------------------------------------------------------------------------
# Calibration Loop
def calibration_loop():
    p_cm_ratio = CONFIG["settings"]["setup"]["p_cm_ratio"]
    message_duration = CONFIG["settings"]["advanced"]["message_duration"]
    global FONT_NAME
    yellow = (255, 255, 0)
    white = (255, 255, 255)
    black = (0, 0, 0)
    font = pygame.font.SysFont(FONT_NAME, 30, bold=True)
    bars = [None, None]
    bars[0] = pygame.Rect(WINDOW_SIZE[0] / 2 - 400, 0, 1, WINDOW_SIZE[1])
    if p_cm_ratio == 1:
        bars[1] = pygame.Rect(WINDOW_SIZE[0] / 2 + 400, 0, 1, WINDOW_SIZE[1])
    else:
        bars[1] = pygame.Rect(bars[0].right + 10 * p_cm_ratio, 0, 1, WINDOW_SIZE[1])
    text = ["Please measure 10 centimeter between the two bars and press enter.",
            "You can change the distance of the bars with the mousewheel."]
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 4:
                    bars[1] = bars[1].move(1, 0)
                elif event.button == 5:
                    bars[1] = bars[1].move(-1, 0)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    global p_cm_input  # Points back into menu, to update it when this closes.
                    p_cm_ratio = (bars[1].left - bars[0].right) / 10
                    CONFIG["settings"]["setup"]["p_cm_ratio"] = p_cm_ratio
                    MESSAGE_TIMERS["Pixel/Centimeter calibrated."] = time.time() + message_duration
                    p_cm_input._input_string = str(p_cm_ratio)
                    with open('config.json', 'w') as outfile:
                        json.dump(CONFIG, outfile, indent=4, default=str)
                    return

        SCREEN.fill(black)

        for i in range(len(bars)):
            pygame.draw.rect(SCREEN, yellow, bars[i])

        for i, l in enumerate(text):
            render = font.render(l, 0, white)
            SCREEN.blit(render, (WINDOW_SIZE[0] / 2 - render.get_size()[0] / 2, 0 + font.get_linesize() * i))
        pygame.display.flip()


def experiment_loop():
    message_duration = CONFIG["settings"]["advanced"]["message_duration"]
    if len(CONFIG["mice"]) == 0:
        MESSAGE_TIMERS["No mouse found."] = time.time() + message_duration
        return

    if len(CONFIG["rats"]) == 0:
        MESSAGE_TIMERS["No rat found."] = time.time() + message_duration
        return

    # Load result storage
    global RESULTS
    with open('results.json') as json_data_file:
        RESULTS = json.load(json_data_file)

    experiment_start = datetime.datetime.now().strftime("%d-%m-%Y (%H:%M:%S.%f)")

    RESULTS[experiment_start] = dict()
    RESULTS[experiment_start]["mouse"] = CURRENT_MOUSE
    RESULTS[experiment_start]["config"] = CONFIG
    RESULTS[experiment_start]["measurements"] = dict()

    # Load font
    font = pygame.font.SysFont(FONT_NAME, 30, bold=True)

    # Prepare background markers
    global SCREEN

    show_fps = True
    target_fps = 60

    black = (0, 0, 0)  # Background-color (black)
    warning_color = (255, 0, 0)  # Warning-color for failed trials (red)
    starting_color = (0, 255, 0)  # Starting-color to mark beginning of a new trial (green)

    ahead_buffer = 2  # Buffered objects in front of the mouse
    onscreen_objects = 4  # Objects currently on-screen
    behind_buffer = 2  # Buffered objects behind the mouse

    marker_height = CONFIG["settings"]["advanced"]["marker_height"]

    screens = screeninfo.get_monitors()

    for screen in screens:
        if screen.x == 0:
            experiment_screen = screen
        else:
            statistics_screen = screen

    latest_line = multiprocessing.Array('f', 3)
    to_recorder, recorder_instructions = multiprocessing.Pipe()
    to_tracer, tracer_instructions = multiprocessing.Pipe()

    instructions = TPM_Utility.Instructions
    go_event = multiprocessing.Event()
    stop_event = multiprocessing.Event()

    experiment_screen_position = (0, 0)

    experiment_screen_size = (experiment_screen.width, experiment_screen.height)

    # Create Screen objects
    experiment_screen = ExperimentScreen(SCREEN, experiment_screen_size, experiment_screen_position,
                                         (ahead_buffer, onscreen_objects, behind_buffer),
                                         marker_height, IMAGE_LIST, font)

    # Load settings
    acceleration_cutoff = CONFIG["settings"]["advanced"]["acceleration_cutoff"]
    reward_abort = CONFIG["settings"]["advanced"]["reward_abort"]
    tube_out = CONFIG["settings"]["hardware"]["tube_out"]
    disk_out = CONFIG["settings"]["hardware"]["disk_out"]
    mouse_lick_in = CONFIG["settings"]["hardware"]["mouse_lick_in"]
    mouse_lick_out = CONFIG["settings"]["hardware"]["mouse_lick_out"]
    rat_lick_in = CONFIG["settings"]["hardware"]["rat_lick_in"]
    rat_lick_out = CONFIG["settings"]["hardware"]["rat_lick_out"]
    if CONFIG["settings"]["setup"]["main_screen_direction_left"]:
        screen_direction = -1
    else:
        screen_direction = 1

    # Prepare visual output (if needed)
    if VIRTUAL_EXPERIMENT:
        user_input = multiprocessing.Queue()
        record_process = multiprocessing.Process(target=TPM_Recorder.virtual_recorder_func, args=(instructions,
                                                                                                  go_event,
                                                                                                  latest_line,
                                                                                                  recorder_instructions,
                                                                                                  user_input))

        visual_output = [[None, None], [None, None]]
        visual_output[0][0] = pygame.transform.rotozoom(pygame.image.load("Tube.gif"), 0, 0.25)
        visual_output[0][1] = pygame.transform.rotozoom(pygame.image.load("Disk.gif"), 0, 0.25)
        visual_output[1][0] = visual_output[0][0].get_rect()
        visual_output[1][0].center = [200, 50]
        visual_output[1][1] = visual_output[0][1].get_rect()
        visual_output[1][1].center = [1000, 50]

    # Else import and prepare the Raspberry Pi communication with the ADC and the PWM pins
    else:
        record_process = multiprocessing.Process(target=TPM_Recorder.analog_recorder_func, args=(instructions,
                                                                                                 go_event,
                                                                                                 latest_line,
                                                                                                 recorder_instructions,
                                                                                                 (mouse_lick_in,
                                                                                                  rat_lick_in)
                                                                                                 ))

        # Prepare the PWM-pin to be written on
        import pigpio
        pi = pigpio.pi()
        pi.hardware_PWM(tube_out, 500, 100000)
        pi.hardware_PWM(disk_out, 500, 100000)
        print("PiGPIO PWM initialized.")

        # Prepare to write the lick-outputs
        pi.set_mode(mouse_lick_out, pigpio.OUTPUT)
        pi.set_mode(rat_lick_out, pigpio.OUTPUT)
        print("PiGPIO output initialized.")

    trace_process = multiprocessing.Process(target=TPM_Statistics.tracer_func, args=(instructions,
                                                                                     go_event, stop_event,
                                                                                     tracer_instructions,
                                                                                     latest_line, statistics_screen))

    trace_process.start()
    # pyautogui.click(10, 10)
    record_process.start()

    # external values and parameters
    speed_multiplier = CONFIG["settings"]["experiment"]["speed_multiplier"]

    p_cm_ratio = CONFIG["settings"]["setup"]["p_cm_ratio"]
    wheel_diameter = CONFIG["settings"]["setup"]["wheel_diameter"]
    tube_distance = CONFIG["settings"]["setup"]["tube_distance"]

    trial_number = CONFIG["settings"]["experiment"]["trial_number"]
    trial_length = CONFIG["settings"]["experiment"]["trial_length"]
    inter_trial_length = CONFIG["settings"]["experiment"]["inter_trial_length"]
    reward_length = CONFIG["settings"]["experiment"]["reward_length"]

    rel_prob_blocked = CONFIG["settings"]["experiment"]["rel_prob_blocked"]
    rel_prob_visual = CONFIG["settings"]["experiment"]["rel_prob_visual"]
    rel_prob_smell = CONFIG["settings"]["experiment"]["rel_prob_smell"]
    rel_prob_opened = CONFIG["settings"]["experiment"]["rel_prob_opened"]

    wheel_circumference = math.pi * wheel_diameter

    disk_random = rel_prob_blocked * [0] + rel_prob_visual * [1] + rel_prob_smell * [2] + rel_prob_opened * [3]
    disk_states = [disk_random[int(len(disk_random) * rdm.random())] for i in range(trial_number)]
    disk_names = ["Blocked", "Visual", "Smell", "Opened"]

    # Loop through trials
    for trial in range(1, trial_number + 1):
        # Preparing storage for this trial
        if not VIRTUAL_EXPERIMENT:
            RESULTS[experiment_start]["measurements"]["trial_" + str(trial)] = dict()
            RESULTS[experiment_start]["measurements"]["trial_" + str(trial)]["phase_transitions"] = []
            RESULTS[experiment_start]["measurements"]["trial_" + str(trial)]["disk_state"] = disk_names[
                disk_states[trial - 1]]
            RESULTS[experiment_start]["measurements"]["trial_" + str(trial)]["trial_phase"]["rat_position"] = []
            RESULTS[experiment_start]["measurements"]["trial_" + str(trial)]["reward_phase"]["records_file"] = ''

        # Writing the disk-movement
        if VIRTUAL_EXPERIMENT:
            visual_output[0][1] = pygame.transform.rotozoom(pygame.image.load("Disk.gif"),
                                                            -90 + disk_states[trial - 1] * -90, 0.25)
            visual_output[1][1] = visual_output[0][1].get_rect()
            visual_output[1][1].center = [1000, 50]
        else:
            pi.hardware_PWM(disk_out, 500, int(disk_states[trial - 1] * 0.25 * 500000) + 100000)

        get_reward = False
        absolute_position = 0

        print("test")

        to_tracer.send(instructions.Reset)
        to_tracer.send(trial_length + reward_length + inter_trial_length)
        to_recorder.send(instructions.Reset)

        if not VIRTUAL_EXPERIMENT:
            to_recorder.send(f'{experiment_start}\trial_{trial}.csv')
            RESULTS[experiment_start]["measurements"]["trial_" + str(trial)][
                "reward_phase"]["records_file"] = f'{experiment_start}\trial_{trial}.csv'

        go_event.clear()
        to_tracer.send(instructions.Ready)
        to_recorder.send(instructions.Ready)
        go_event.wait()

        tube_position = 0
        old_position_volt = latest_line[1]
        old_delta_position_volt = 0

        trial_start = time.perf_counter()
        last_frame = trial_start
        trial_end = trial_start + trial_length

        if show_fps:
            start_time = trial_start
            x = 0.5
            counter = 0
            text_surface = pygame.Surface((100, 100))

        if not VIRTUAL_EXPERIMENT:
            RESULTS[experiment_start]["measurements"]["trial_" + str(trial)]["phase_transitions"].append(latest_line[0])

        # Trial-phase loop
        while time.perf_counter() < trial_end:
            # Event handling
            if stop_event.is_set():
                break
            if not go_event.is_set():
                to_recorder.send(instructions.Pause)
                to_tracer.send(instructions.Pause)
            go_event.wait()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()

                # Virtual input
                if VIRTUAL_EXPERIMENT and event.type == pygame.MOUSEBUTTONDOWN:
                    user_input.put(event.button)

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if not VIRTUAL_EXPERIMENT:
                            save_results()
                            pi.hardware_PWM(tube_out, 500, 100000)

                        to_tracer.send(instructions.Dump)
                        print('tracer told to stop')
                        to_tracer.send(instructions.Stop)
                        print('recorder told to stop')
                        to_recorder.send(instructions.Stop)
                        trace_process.join()
                        record_process.join()

                        MESSAGE_TIMERS["Experiment ended."] = time.time() + message_duration
                        return

            if stop_event.is_set():
                if not VIRTUAL_EXPERIMENT:
                    save_results()
                    pi.hardware_PWM(tube_out, 500, 100000)

                to_tracer.send(instructions.Dump)
                print('tracer told to stop')
                to_tracer.send(instructions.Stop)
                print('recorder told to stop')
                to_recorder.send(instructions.Stop)
                trace_process.join()
                record_process.join()

                MESSAGE_TIMERS["Experiment ended."] = time.time() + message_duration
                return

            # Filling screen and showing starting signal
            if time.time() < trial_start + 1.2:
                if int((time.time() - trial_start) / 0.2) % 2 != 0:
                    SCREEN.fill(starting_color)
                else:
                    SCREEN.fill(black)
            else:
                SCREEN.fill(black)
            clock.tick(target_fps)

            position_volt = latest_line[1]
            this_frame = time.perf_counter()
            delta_position_volt = position_volt - old_position_volt
            old_position_volt = position_volt
            delta2_position_volt = delta_position_volt - old_delta_position_volt

            if abs(delta2_position_volt) > acceleration_cutoff:
                continue

            delta_position_real = delta_position_volt / 5.033 * wheel_circumference

            if abs(speed_multiplier * p_cm_ratio * delta_position_real) > 1:
                tube_position += speed_multiplier * delta_position_real
            if tube_position < 0:
                tube_position = 0
            elif tube_position > 0.95 * tube_distance:
                tube_position = tube_distance

            if not VIRTUAL_EXPERIMENT:
                pi.hardware_PWM(tube_out, 500, int(tube_position / tube_distance * 500000) + 100000)

            absolute_position += delta_position_real

            text = ["Phase: Trial",
                    f"Screen speed: {speed_multiplier * delta_position_real / (this_frame - last_frame)}",
                    f"Volt position [in V]: {position_volt}",
                    f"Volt delta [in V]: {delta_position_volt}",
                    f"Virtual position [in cm]: {tube_position}",
                    f"Current disk state: {disk_names[disk_states[trial - 1]]}"]

            last_frame = this_frame

            if tube_position == tube_distance:
                get_reward = True
                break

            # Moving the markers
            experiment_screen.move(screen_direction * speed_multiplier * p_cm_ratio * delta_position_real)
            experiment_screen.blit_to_parent()

            for i, l in enumerate(text):
                render = font.render(l, 0, (255, 255, 255))
                SCREEN.blit(render, (WINDOW_SIZE[0] - render.get_size()[0], 0 + font.get_linesize() * i))

            if VIRTUAL_EXPERIMENT:
                visual_output[1][0].center = [200 + 20 * tube_position, 50]
                SCREEN.blit(visual_output[0][0], visual_output[1][0])
                SCREEN.blit(visual_output[0][1], visual_output[1][1])

            if show_fps:
                counter += 1
                if (time.perf_counter() - start_time) > x:
                    my_font = pygame.font.SysFont('Comic Sans MS', 30)
                    text_surface = my_font.render(f'FPS: {int(counter / (time.perf_counter() - start_time))}',
                                                  False, (255, 255, 255))
                    start_time = time.perf_counter()
                    counter = 0

                SCREEN.blit(text_surface, (0, 0))

            pygame.display.flip()

        if get_reward:
            to_tracer.send(instructions.Phase)
            to_tracer.send('Reward')

            if not VIRTUAL_EXPERIMENT:
                RESULTS[experiment_start]["measurements"]["trial_" + str(trial)]["phase_transitions"].append(
                    latest_line[0])

            reward_start = time.perf_counter()
            reward_end = reward_start + reward_length
            has_licked = False

            # Reward-phase loop
            while time.perf_counter() < reward_end:
                # Event handling
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        sys.exit()

                    # Virtual input
                    if VIRTUAL_EXPERIMENT and event.type == pygame.MOUSEBUTTONDOWN:
                        user_input.put(event.button)

                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            if not VIRTUAL_EXPERIMENT:
                                save_results()
                                pi.hardware_PWM(tube_out, 500, 100000)

                            to_tracer.send(instructions.Dump)
                            print('tracer told to stop')
                            to_tracer.send(instructions.Stop)
                            print('recorder told to stop')
                            to_recorder.send(instructions.Stop)
                            trace_process.join()
                            record_process.join()

                            MESSAGE_TIMERS["Experiment ended."] = time.time() + message_duration
                            return

                if stop_event.is_set():
                    if not VIRTUAL_EXPERIMENT:
                        save_results()
                        pi.hardware_PWM(tube_out, 500, 100000)

                    to_tracer.send(instructions.Dump)
                    print('tracer told to stop')
                    to_tracer.send(instructions.Stop)
                    print('recorder told to stop')
                    to_recorder.send(instructions.Stop)
                    trace_process.join()
                    record_process.join()

                    MESSAGE_TIMERS["Experiment ended."] = time.time() + message_duration
                    return

                # Filling screen
                SCREEN.fill(black)

                position_volt = latest_line[1]
                this_frame = time.perf_counter()
                delta_position_volt = position_volt - old_position_volt
                old_position_volt = position_volt
                delta2_position_volt = delta_position_volt - old_delta_position_volt

                if abs(delta2_position_volt) > acceleration_cutoff:
                    continue

                delta_position_real = delta_position_volt / 5.033 * wheel_circumference

                if abs(speed_multiplier * p_cm_ratio * delta_position_real) > 1:
                    tube_position += speed_multiplier * delta_position_real
                if tube_position < 0:
                    tube_position = 0
                elif tube_position > 0.95 * tube_distance:
                    tube_position = tube_distance

                if not VIRTUAL_EXPERIMENT:
                    pi.hardware_PWM(tube_out, 500, int(tube_position / tube_distance * 500000) + 100000)

                absolute_position += delta_position_real

                text = ["Phase: Reward",
                        f"Screen speed: {speed_multiplier * delta_position_real / (this_frame - last_frame)}",
                        f"Volt position [in V]: {position_volt}",
                        f"Volt delta [in V]: {delta_position_volt}",
                        f"Virtual position [in cm]: {tube_position}",
                        f"Current disk state: {disk_names[disk_states[trial - 1]]}"]

                last_frame = this_frame

                for i, l in enumerate(text):
                    render = font.render(l, 0, (255, 255, 255))
                    SCREEN.blit(render, (WINDOW_SIZE[0] - render.get_size()[0], 0 + font.get_linesize() * i))

                # Moving the markers
                experiment_screen.move(screen_direction * speed_multiplier * p_cm_ratio * delta_position_real)
                experiment_screen.blit_to_parent()

                for i, l in enumerate(text):
                    render = font.render(l, 0, (255, 255, 255))
                    SCREEN.blit(render, (WINDOW_SIZE[0] - render.get_size()[0], 0 + font.get_linesize() * i))

                if VIRTUAL_EXPERIMENT:
                    visual_output[1][0].center = [200 + 20 * tube_position, 50]
                    SCREEN.blit(visual_output[0][0], visual_output[1][0])
                    SCREEN.blit(visual_output[0][1], visual_output[1][1])

                if show_fps:
                    counter += 1
                    if (time.perf_counter() - start_time) > x:
                        my_font = pygame.font.SysFont('Comic Sans MS', 30)
                        text_surface = my_font.render(f'FPS: {int(counter / (time.perf_counter() - start_time))}',
                                                      False, (255, 255, 255))
                        start_time = time.perf_counter()
                        counter = 0

                    SCREEN.blit(text_surface, (0, 0))

                pygame.display.flip()

        # Inter-trial-phase loop
        if len(screens) > 1:
            to_tracer.send(instructions.Phase)
            to_tracer.send('Inter-Trial')

        if not VIRTUAL_EXPERIMENT:
            RESULTS[experiment_start]["measurements"]["trial_" + str(trial)]["phase_transitions"].append(latest_line[0])

        inter_trial_start = time.perf_counter()
        inter_trial_end = inter_trial_start + inter_trial_length

        while time.perf_counter() < inter_trial_end:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()

                # Virtual input
                if VIRTUAL_EXPERIMENT and event.type == pygame.MOUSEBUTTONDOWN:
                    user_input.put(event.button)

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if not VIRTUAL_EXPERIMENT:
                            save_results()
                            pi.hardware_PWM(tube_out, 500, 100000)

                        to_tracer.send(instructions.Dump)
                        print('tracer told to stop')
                        to_tracer.send(instructions.Stop)
                        print('recorder told to stop')
                        to_recorder.send(instructions.Stop)
                        trace_process.join()
                        record_process.join()

                        MESSAGE_TIMERS["Experiment ended."] = time.time() + message_duration
                        return

            if stop_event.is_set():
                if not VIRTUAL_EXPERIMENT:
                    save_results()
                    pi.hardware_PWM(tube_out, 500, 100000)

                to_tracer.send(instructions.Dump)
                print('tracer told to stop')
                to_tracer.send(instructions.Stop)
                print('recorder told to stop')
                to_recorder.send(instructions.Stop)
                trace_process.join()
                record_process.join()

                MESSAGE_TIMERS["Experiment ended."] = time.time() + message_duration
                return

            # Filling screen
            if not get_reward and time.time() < inter_trial_start + 1.2:
                if int((time.time() - inter_trial_start) / 0.2) % 2 != 0:
                    SCREEN.fill(warning_color)
                else:
                    SCREEN.fill(black)
            else:
                SCREEN.fill(black)

            position_volt = latest_line[1]
            this_frame = time.perf_counter()
            delta_position_volt = position_volt - old_position_volt
            old_position_volt = position_volt
            delta2_position_volt = delta_position_volt - old_delta_position_volt

            if abs(delta2_position_volt) > acceleration_cutoff:
                continue

            delta_position_real = delta_position_volt / 5.033 * wheel_circumference

            if abs(speed_multiplier * p_cm_ratio * delta_position_real) > 1:
                tube_position += speed_multiplier * delta_position_real
            if tube_position < 0:
                tube_position = 0
            elif tube_position > 0.95 * tube_distance:
                tube_position = tube_distance

            if VIRTUAL_EXPERIMENT:
                visual_output[1][0].center = [200 + 20 * tube_position, 50]
                SCREEN.blit(visual_output[0][0], visual_output[1][0])
                SCREEN.blit(visual_output[0][1], visual_output[1][1])

            else:
                pi.hardware_PWM(tube_out, 500, 100000)

            absolute_position += delta_position_real

            text = ["Phase: Inter-Trial",
                    f"Screen speed: {speed_multiplier * delta_position_real / (this_frame - last_frame)}",
                    f"Volt position [in V]: {position_volt}",
                    f"Volt delta [in V]: {delta_position_volt}",
                    f"Virtual position [in cm]: {tube_position}",
                    f"Current disk state: {disk_names[disk_states[trial - 1]]}"]

            last_frame = this_frame
            for i, l in enumerate(text):
                render = font.render(l, 0, (255, 255, 255))
                SCREEN.blit(render, (WINDOW_SIZE[0] - render.get_size()[0], 0 + font.get_linesize() * i))

            # Moving the markers
            experiment_screen.move(screen_direction * speed_multiplier * p_cm_ratio * delta_position_real)
            experiment_screen.blit_to_parent()

            for i, l in enumerate(text):
                render = font.render(l, 0, (255, 255, 255))
                SCREEN.blit(render, (WINDOW_SIZE[0] - render.get_size()[0], 0 + font.get_linesize() * i))

            if VIRTUAL_EXPERIMENT:
                visual_output[1][0].center = [200 + 20 * tube_position, 50]
                SCREEN.blit(visual_output[0][0], visual_output[1][0])
                SCREEN.blit(visual_output[0][1], visual_output[1][1])

            if show_fps:
                counter += 1
                if (time.perf_counter() - start_time) > x:
                    my_font = pygame.font.SysFont('Comic Sans MS', 30)
                    text_surface = my_font.render(f'FPS: {int(counter / (time.perf_counter() - start_time))}',
                                                  False, (255, 255, 255))
                    start_time = time.perf_counter()
                    counter = 0

                SCREEN.blit(text_surface, (0, 0))

            pygame.display.flip()

    save_results()
    MESSAGE_TIMERS["Experiment finished."] = time.time() + message_duration


def pairing_mouse_loop():
    pass


def pairing_rat_loop():
    pass


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------
def main(test=False):
    # -------------------------------------------------------------------------
    # Globals
    # -------------------------------------------------------------------------
    global clock
    global main_menu
    global SCREEN
    global CONFIG
    global CURRENT_MOUSE
    global MOUSE_NR
    global MOUSE_INFO
    global CURRENT_RAT
    global RAT_NR
    global RAT_INFO
    global WINDOW_SIZE
    global FONT_NAME
    global MAIN_MENUBAR
    global EXPERIMENT_MENUBAR
    global PAIRING_MENUBAR
    global HARDWARE_MENUBAR

    # -------------------------------------------------------------------------
    # Reading config
    # -------------------------------------------------------------------------
    with open('config.json') as json_data_file:
        CONFIG = json.load(json_data_file)
    message_duration = CONFIG["settings"]["advanced"]["message_duration"]
    MOUSE_NR = 0
    RAT_NR = 0
    FONT_NAME = CONFIG["settings"]["advanced"]["font_name"]
    if len(CONFIG["mice"]) > 0:
        CURRENT_MOUSE = list(CONFIG["mice"].keys())[MOUSE_NR]
        MOUSE_INFO = ['Name: {0}'.format(CONFIG["mice"][CURRENT_MOUSE]["name"]),
                      'Date of Birth: {0}'.format(CONFIG["mice"][CURRENT_MOUSE]["dob"]),
                      'Starting Weight: {0}g'.format(CONFIG["mice"][CURRENT_MOUSE]["weight"])]
    if len(CONFIG["rats"]) > 0:
        CURRENT_RAT = list(CONFIG["rats"].keys())[RAT_NR]
        RAT_INFO = ['Name: {0}'.format(CONFIG["rats"][CURRENT_RAT]["name"]),
                    'Date of Birth: {0}'.format(CONFIG["rats"][CURRENT_RAT]["dob"]),
                    'Starting Weight: {0}g'.format(CONFIG["rats"][CURRENT_RAT]["weight"])]

    # -------------------------------------------------------------------------
    # Init pygame
    # -------------------------------------------------------------------------
    pygame.init()

    # Create pygame screen and objects
    os.environ['SDL_VIDEO_CENTERED'] = '1'

    screens = screeninfo.get_monitors()
    experiment_screen = None
    for screen in screens:
        if screen.x == 0:
            experiment_screen = screen

    SCREEN = pygame.display.set_mode((experiment_screen.width, experiment_screen.height),
                                     pygame.NOFRAME | pygame.HWSURFACE | pygame.DOUBLEBUF)

    WINDOW_SIZE = SCREEN.get_size()
    pygame.display.set_caption('Uncertainty Project')
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    matches = find_font_file(FONT_NAME)
    if FONT_NAME.casefold() == "none" or not matches:
        FONT_NAME = pygame.font.get_fonts()[0]
        font_location = find_font_file(pygame.font.get_fonts()[0])[0]
        print("Font None or no matches. Using " + FONT_NAME + " system font.")
    else:
        font_location = matches[0]

    # -------------------------------------------------------------------------
    # Init performance plot
    # -------------------------------------------------------------------------
    performance_figure = plt.figure(figsize=[4.5, 2.2], facecolor=tuple([x / 255 for x in MENU_BACKGROUND_COLOR]))
    ax = performance_figure.add_subplot(111)
    ax.patch.set_facecolor(tuple([x / 255 for x in MENU_BACKGROUND_COLOR]))
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_visible(True)
    ax.spines['left'].set_visible(True)

    days = matplotlib.dates.DayLocator()  # every month
    days_fmt = matplotlib.dates.DateFormatter('%d.%m')
    ax.xaxis.set_major_locator(days)
    ax.xaxis.set_major_formatter(days_fmt)

    # -------------------------------------------------------------------------
    # Create menus
    # -------------------------------------------------------------------------
    # Main menu
    main_menu = pygameMenu.Menu(SCREEN,
                                bgfun=main_background,
                                color_selected=COLOR_WHITE,
                                font=font_location,
                                font_color=COLOR_BLACK,
                                font_size=30,
                                menu_alpha=100,
                                menu_color=MENU_BACKGROUND_COLOR,
                                menu_height=int(MENU_SIZE[1] * 0.6),
                                menu_width=int(MENU_SIZE[0] * 0.6),
                                mouse_visible=False,
                                onclose=pygameMenu.events.DISABLE_CLOSE,
                                option_shadow=False,
                                title='Main Menu',
                                window_height=WINDOW_SIZE[1],
                                window_width=WINDOW_SIZE[0]
                                )

    # Menu for selecting the Mouse and Rat used in the experiment
    experiment_profile_menu = pygameMenu.TextMenu(SCREEN,
                                                  bgfun=main_background,
                                                  color_selected=COLOR_WHITE,
                                                  font=font_location,
                                                  font_color=COLOR_BLACK,
                                                  font_size=30,
                                                  menu_alpha=0,
                                                  menu_color=MENU_BACKGROUND_COLOR,
                                                  menu_height=int(MENU_SIZE[1] * 1.25),
                                                  menu_width=int(MENU_SIZE[0] * 0.8),
                                                  mouse_visible=False,
                                                  onclose=pygameMenu.events.DISABLE_CLOSE,
                                                  option_shadow=False,
                                                  title='Select Animals',
                                                  text_color=COLOR_BLACK,
                                                  text_fontsize=30,
                                                  text_align=pygameMenu.locals.ALIGN_CENTER,
                                                  window_height=WINDOW_SIZE[1],
                                                  window_width=WINDOW_SIZE[0]
                                                  )

    # Menu for starting the experiment
    experiment_start_menu = pygameMenu.TextMenu(SCREEN,
                                                bgfun=main_background,
                                                color_selected=COLOR_WHITE,
                                                font=font_location,
                                                font_color=COLOR_BLACK,
                                                font_size=30,
                                                menu_alpha=100,
                                                menu_color=MENU_BACKGROUND_COLOR,
                                                menu_height=int(MENU_SIZE[1] * 1.45),
                                                menu_width=int(MENU_SIZE[0] * 0.8),
                                                mouse_visible=False,
                                                onclose=pygameMenu.events.DISABLE_CLOSE,
                                                option_shadow=False,
                                                title='Start Experiment',
                                                text_color=COLOR_BLACK,
                                                text_fontsize=30,
                                                text_align=pygameMenu.locals.ALIGN_CENTER,
                                                window_height=WINDOW_SIZE[1],
                                                window_width=WINDOW_SIZE[0]
                                                )

    # Menu for setting the experiment parameters
    experiment_parameter_menu = pygameMenu.Menu(SCREEN,
                                                bgfun=main_background,
                                                color_selected=COLOR_WHITE,
                                                font=font_location,
                                                font_color=COLOR_BLACK,
                                                font_size=30,
                                                menu_alpha=100,
                                                menu_color=MENU_BACKGROUND_COLOR,
                                                menu_height=int(MENU_SIZE[1] * 1.35),
                                                menu_width=int(MENU_SIZE[0] * 0.8),
                                                mouse_visible=False,
                                                onclose=pygameMenu.events.DISABLE_CLOSE,
                                                option_shadow=False,
                                                title='Change Parameters',
                                                window_height=WINDOW_SIZE[1],
                                                window_width=WINDOW_SIZE[0]
                                                )

    # Menu for selecting the Mouse or Rat used in the pairing
    pairing_profile_menu = pygameMenu.TextMenu(SCREEN,
                                               bgfun=main_background,
                                               color_selected=COLOR_WHITE,
                                               font=font_location,
                                               font_color=COLOR_BLACK,
                                               font_size=30,
                                               menu_alpha=0,
                                               menu_color=MENU_BACKGROUND_COLOR,
                                               menu_height=int(MENU_SIZE[1] * 1.25),
                                               menu_width=int(MENU_SIZE[0] * 0.8),
                                               mouse_visible=False,
                                               onclose=pygameMenu.events.DISABLE_CLOSE,
                                               option_shadow=False,
                                               title='Select Mouse',
                                               text_color=COLOR_BLACK,
                                               text_fontsize=30,
                                               text_align=pygameMenu.locals.ALIGN_CENTER,
                                               window_height=WINDOW_SIZE[1],
                                               window_width=WINDOW_SIZE[0]
                                               )

    # Menu for starting the Mouse pairing
    pairing_mouse_start_menu = pygameMenu.TextMenu(SCREEN,
                                                   bgfun=main_background,
                                                   color_selected=COLOR_WHITE,
                                                   font=font_location,
                                                   font_color=COLOR_BLACK,
                                                   font_size=30,
                                                   menu_alpha=100,
                                                   menu_color=MENU_BACKGROUND_COLOR,
                                                   menu_height=int(MENU_SIZE[1] * 1.45),
                                                   menu_width=int(MENU_SIZE[0] * 0.8),
                                                   mouse_visible=False,
                                                   onclose=pygameMenu.events.DISABLE_CLOSE,
                                                   option_shadow=False,
                                                   title='Start Mouse Pairing',
                                                   text_color=COLOR_BLACK,
                                                   text_fontsize=30,
                                                   text_align=pygameMenu.locals.ALIGN_CENTER,
                                                   window_height=WINDOW_SIZE[1],
                                                   window_width=WINDOW_SIZE[0]
                                                   )

    # Menu for setting the Mouse pairing parameters
    pairing_mouse_parameter_menu = pygameMenu.Menu(SCREEN,
                                                   bgfun=main_background,
                                                   color_selected=COLOR_WHITE,
                                                   font=font_location,
                                                   font_color=COLOR_BLACK,
                                                   font_size=30,
                                                   menu_alpha=100,
                                                   menu_color=MENU_BACKGROUND_COLOR,
                                                   menu_height=int(MENU_SIZE[1] * 1.35),
                                                   menu_width=int(MENU_SIZE[0] * 0.8),
                                                   mouse_visible=False,
                                                   onclose=pygameMenu.events.DISABLE_CLOSE,
                                                   option_shadow=False,
                                                   title='Change Parameters',
                                                   window_height=WINDOW_SIZE[1],
                                                   window_width=WINDOW_SIZE[0]
                                                   )

    # Menu for starting the Rat pairing
    pairing_rat_start_menu = pygameMenu.TextMenu(SCREEN,
                                                 bgfun=main_background,
                                                 color_selected=COLOR_WHITE,
                                                 font=font_location,
                                                 font_color=COLOR_BLACK,
                                                 font_size=30,
                                                 menu_alpha=100,
                                                 menu_color=MENU_BACKGROUND_COLOR,
                                                 menu_height=int(MENU_SIZE[1] * 1.45),
                                                 menu_width=int(MENU_SIZE[0] * 0.8),
                                                 mouse_visible=False,
                                                 onclose=pygameMenu.events.DISABLE_CLOSE,
                                                 option_shadow=False,
                                                 title='Start Rat Pairing',
                                                 text_color=COLOR_BLACK,
                                                 text_fontsize=30,
                                                 text_align=pygameMenu.locals.ALIGN_CENTER,
                                                 window_height=WINDOW_SIZE[1],
                                                 window_width=WINDOW_SIZE[0]
                                                 )

    # Menu for setting the Rat pairing parameters
    pairing_rat_parameter_menu = pygameMenu.Menu(SCREEN,
                                                 bgfun=main_background,
                                                 color_selected=COLOR_WHITE,
                                                 font=font_location,
                                                 font_color=COLOR_BLACK,
                                                 font_size=30,
                                                 menu_alpha=100,
                                                 menu_color=MENU_BACKGROUND_COLOR,
                                                 menu_height=int(MENU_SIZE[1] * 1.35),
                                                 menu_width=int(MENU_SIZE[0] * 0.8),
                                                 mouse_visible=False,
                                                 onclose=pygameMenu.events.DISABLE_CLOSE,
                                                 option_shadow=False,
                                                 title='Change Parameters',
                                                 window_height=WINDOW_SIZE[1],
                                                 window_width=WINDOW_SIZE[0]
                                                 )

    # Menu to navigate the different categories of settings
    settings_menu = pygameMenu.Menu(SCREEN,
                                    bgfun=main_background,
                                    color_selected=COLOR_WHITE,
                                    font=font_location,
                                    font_color=COLOR_BLACK,
                                    font_size=30,
                                    menu_alpha=100,
                                    menu_color=MENU_BACKGROUND_COLOR,
                                    menu_height=int(MENU_SIZE[1] * 0.8),
                                    menu_width=int(MENU_SIZE[0] * 0.8),
                                    mouse_visible=False,
                                    onclose=pygameMenu.events.DISABLE_CLOSE,
                                    option_shadow=False,
                                    title='Settings Overview',
                                    window_height=WINDOW_SIZE[1],
                                    window_width=WINDOW_SIZE[0]
                                    )

    # Menu to set setup specific parameters
    setup_settings_menu = pygameMenu.Menu(SCREEN,
                                          bgfun=main_background,
                                          color_selected=COLOR_WHITE,
                                          font=font_location,
                                          font_color=COLOR_BLACK,
                                          font_size=30,
                                          menu_alpha=100,
                                          menu_color=MENU_BACKGROUND_COLOR,
                                          menu_height=int(MENU_SIZE[1] * 0.8),
                                          menu_width=int(MENU_SIZE[0] * 0.8),
                                          mouse_visible=False,
                                          onclose=pygameMenu.events.DISABLE_CLOSE,
                                          option_shadow=False,
                                          title='Setup Settings',
                                          window_height=WINDOW_SIZE[1],
                                          window_width=WINDOW_SIZE[0]
                                          )

    # Menu to set the used pins
    hardware_settings_menu = pygameMenu.Menu(SCREEN,
                                             bgfun=main_background,
                                             color_selected=COLOR_WHITE,
                                             font=font_location,
                                             font_color=COLOR_BLACK,
                                             font_size=30,
                                             menu_alpha=0,
                                             menu_color=MENU_BACKGROUND_COLOR,
                                             menu_height=int(MENU_SIZE[1] * 2),
                                             menu_width=int(MENU_SIZE[0] * 1.5),
                                             mouse_visible=False,
                                             onclose=pygameMenu.events.DISABLE_CLOSE,
                                             option_shadow=False,
                                             title='Hardware Settings',
                                             window_height=int(WINDOW_SIZE[1] * 1.2),
                                             window_width=WINDOW_SIZE[0]
                                             )

    # Menu to set setup specific parameters
    advanced_settings_menu = pygameMenu.Menu(SCREEN,
                                             bgfun=main_background,
                                             color_selected=COLOR_WHITE,
                                             font=font_location,
                                             font_color=COLOR_BLACK,
                                             font_size=30,
                                             menu_alpha=100,
                                             menu_color=MENU_BACKGROUND_COLOR,
                                             menu_height=int(MENU_SIZE[1] * 0.8),
                                             menu_width=int(MENU_SIZE[0] * 0.8),
                                             mouse_visible=False,
                                             onclose=pygameMenu.events.DISABLE_CLOSE,
                                             option_shadow=False,
                                             title='Advanced Settings',
                                             window_height=WINDOW_SIZE[1],
                                             window_width=WINDOW_SIZE[0]
                                             )

    # Menu for the mouse profiles
    mouse_menu = pygameMenu.TextMenu(SCREEN,
                                     bgfun=main_background,
                                     color_selected=COLOR_WHITE,
                                     font=font_location,
                                     font_color=COLOR_BLACK,
                                     font_size=30,
                                     menu_alpha=100,
                                     menu_color=MENU_BACKGROUND_COLOR,
                                     menu_height=int(MENU_SIZE[1] * 0.9),
                                     menu_width=int(MENU_SIZE[0] * 0.8),
                                     onclose=pygameMenu.events.DISABLE_CLOSE,
                                     option_shadow=False,
                                     title='Mouse Profiles',
                                     text_color=COLOR_BLACK,
                                     text_fontsize=30,
                                     text_align=pygameMenu.locals.ALIGN_CENTER,
                                     window_height=WINDOW_SIZE[1],
                                     window_width=WINDOW_SIZE[0]
                                     )

    # Menu to add a mouse to the profiles
    add_mouse_menu = pygameMenu.Menu(SCREEN,
                                     bgfun=main_background,
                                     color_selected=COLOR_WHITE,
                                     font=font_location,
                                     font_color=COLOR_BLACK,
                                     font_size=30,
                                     menu_alpha=100,
                                     menu_color=MENU_BACKGROUND_COLOR,
                                     menu_height=int(MENU_SIZE[1] * 0.8),
                                     menu_width=int(MENU_SIZE[0] * 0.95),
                                     mouse_visible=False,
                                     onclose=pygameMenu.events.DISABLE_CLOSE,
                                     option_shadow=False,
                                     title='Add Mouse',
                                     window_height=WINDOW_SIZE[1],
                                     window_width=WINDOW_SIZE[0]
                                     )

    # Menu to remove a mouse from the profiles
    remove_mouse_menu = pygameMenu.TextMenu(SCREEN,
                                            bgfun=main_background,
                                            color_selected=COLOR_WHITE,
                                            font=font_location,
                                            font_color=COLOR_BLACK,
                                            font_size=30,
                                            menu_alpha=100,
                                            menu_color=MENU_BACKGROUND_COLOR,
                                            menu_height=int(MENU_SIZE[1] * 1),
                                            menu_width=int(MENU_SIZE[0] * 1.1),
                                            mouse_visible=False,
                                            onclose=pygameMenu.events.DISABLE_CLOSE,
                                            option_shadow=False,
                                            title='Remove Mouse',
                                            text_color=COLOR_BLACK,
                                            text_fontsize=30,
                                            window_height=WINDOW_SIZE[1],
                                            window_width=WINDOW_SIZE[0]
                                            )

    # Menu for the rat profiles
    rat_menu = pygameMenu.TextMenu(SCREEN,
                                   bgfun=main_background,
                                   color_selected=COLOR_WHITE,
                                   font=font_location,
                                   font_color=COLOR_BLACK,
                                   font_size=30,
                                   menu_alpha=100,
                                   menu_color=MENU_BACKGROUND_COLOR,
                                   menu_height=int(MENU_SIZE[1] * 0.9),
                                   menu_width=int(MENU_SIZE[0] * 0.8),
                                   onclose=pygameMenu.events.DISABLE_CLOSE,
                                   option_shadow=False,
                                   title='Rat Profiles',
                                   text_color=COLOR_BLACK,
                                   text_fontsize=30,
                                   text_align=pygameMenu.locals.ALIGN_CENTER,
                                   window_height=WINDOW_SIZE[1],
                                   window_width=WINDOW_SIZE[0]
                                   )

    # Menu to add a rat to the profiles
    add_rat_menu = pygameMenu.Menu(SCREEN,
                                   bgfun=main_background,
                                   color_selected=COLOR_WHITE,
                                   font=font_location,
                                   font_color=COLOR_BLACK,
                                   font_size=30,
                                   menu_alpha=100,
                                   menu_color=MENU_BACKGROUND_COLOR,
                                   menu_height=int(MENU_SIZE[1] * 0.8),
                                   menu_width=int(MENU_SIZE[0] * 0.95),
                                   mouse_visible=False,
                                   onclose=pygameMenu.events.DISABLE_CLOSE,
                                   option_shadow=False,
                                   title='Add Rat',
                                   window_height=WINDOW_SIZE[1],
                                   window_width=WINDOW_SIZE[0]
                                   )

    # Menu to remove a rat from the profiles
    remove_rat_menu = pygameMenu.TextMenu(SCREEN,
                                          bgfun=main_background,
                                          color_selected=COLOR_WHITE,
                                          font=font_location,
                                          font_color=COLOR_BLACK,
                                          font_size=30,
                                          menu_alpha=100,
                                          menu_color=MENU_BACKGROUND_COLOR,
                                          menu_height=int(MENU_SIZE[1] * 1),
                                          menu_width=int(MENU_SIZE[0] * 1.1),
                                          mouse_visible=False,
                                          onclose=pygameMenu.events.DISABLE_CLOSE,
                                          option_shadow=False,
                                          title='Remove Rat',
                                          text_color=COLOR_BLACK,
                                          text_fontsize=30,
                                          window_height=WINDOW_SIZE[1],
                                          window_width=WINDOW_SIZE[0]
                                          )

    # Menu for information about coding and hardware
    about_menu = pygameMenu.TextMenu(SCREEN,
                                     bgfun=main_background,
                                     color_selected=COLOR_WHITE,
                                     font=font_location,
                                     font_color=COLOR_BLACK,
                                     font_size=30,
                                     menu_alpha=100,
                                     menu_color=MENU_BACKGROUND_COLOR,
                                     menu_height=int(MENU_SIZE[1] * 1.6),
                                     menu_width=int(MENU_SIZE[0] * 1.2),
                                     mouse_visible=False,
                                     onclose=pygameMenu.events.DISABLE_CLOSE,
                                     option_shadow=False,
                                     title='About',
                                     text_color=COLOR_BLACK,
                                     text_fontsize=30,
                                     window_height=WINDOW_SIZE[1],
                                     window_width=WINDOW_SIZE[0]
                                     )

    # -------------------------------------------------------------------------
    # Menu functions
    # -------------------------------------------------------------------------
    def save_config(*args):
        global CONFIG
        global MESSAGE_TIMERS
        with open('config.json', 'w') as outfile:
            json.dump(CONFIG, outfile, indent=4, default=str)
        MESSAGE_TIMERS["Config saved."] = time.time() + message_duration

    # Main Menu
    def main_menu_fork(value, sub_menu, **kwargs):
        main_menu._open(sub_menu)

    # Experiment Parameter Menu
    def update_experiment_start_menu(*args):
        global VIRTUAL_EXPERIMENT
        input_data = experiment_parameter_menu.get_input_data()
        for key in input_data.keys():
            if key == "virtual_experiment":
                if input_data[key][0] == "Yes":
                    VIRTUAL_EXPERIMENT = True
                else:
                    VIRTUAL_EXPERIMENT = False
                continue
            CONFIG["settings"]["experiment"][key] = input_data[key]

        experiment_start_menu._text = \
            ['Run a virtual experiment?: {0}'.format("Yes" if VIRTUAL_EXPERIMENT else "No"),
             'Number of trials: {0}'.format(CONFIG["settings"]["experiment"]["trial_number"]),
             'Trial length: {0}s'.format(CONFIG["settings"]["experiment"]["trial_length"]),
             'Inter-Trial length: {0}s'.format(CONFIG["settings"]["experiment"]["inter_trial_length"]),
             'Reward length: {0}s'.format(CONFIG["settings"]["experiment"]["reward_length"]),
             'Reward timer for rat: {0}s'.format(CONFIG["settings"]["experiment"]["reward_timer_rat"]),
             'Speed multiplier: {0}x'.format(CONFIG["settings"]["experiment"]["speed_multiplier"]),
             'Rel. prob. Blocked: {0}'.format(CONFIG["settings"]["experiment"]["rel_prob_blocked"]),
             'Rel. prob. Visual: {0}'.format(CONFIG["settings"]["experiment"]["rel_prob_visual"]),
             'Rel. prob. Smell: {0}'.format(CONFIG["settings"]["experiment"]["rel_prob_smell"]),
             'Rel. prob. Opened: {0}'.format(CONFIG["settings"]["experiment"]["rel_prob_opened"])]

    # Pairing Menu
    def change_pairing_type(value, *args, **kwargs):
        selected, index = value
        if selected == "Mouse":
            pairing_profile_menu._menubar.set_title("Select Mouse")
            pairing_selector_profile._label = "Mouse: "
            pairing_selector_profile._elements = [(val, CONFIG["mice"][val]["name"]) for val in
                                                  list(CONFIG["mice"].keys())]
            pairing_selector_profile._index = MOUSE_NR

            if len(CONFIG["mice"]) > 0:
                pairing_profile_menu._text = \
                    [item for sublist in [
                        MOUSE_INFO,
                        [pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE]
                    ] for item in sublist]
                if not CONFIG["mice"][CURRENT_MOUSE]["pairing_duration"].keys():
                    pairing_profile_menu._text[5] = "No pairing records found."

            else:
                pairing_profile_menu._text = ["No Mouse profiles found.",
                                              "Add a Mouse to proceed.",
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE]

        else:
            pairing_profile_menu._menubar.set_title("Select Rat")
            pairing_selector_profile._label = "Rat: "
            pairing_selector_profile._elements = [(val, CONFIG["rats"][val]["name"]) for val in
                                                  list(CONFIG["rats"].keys())]
            pairing_selector_profile._index = RAT_NR

            if len(CONFIG["rats"]) > 0:
                pairing_profile_menu._text = \
                    [item for sublist in [
                        RAT_INFO,
                        [pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE]
                    ] for item in sublist]
                if not CONFIG["rats"][CURRENT_RAT]["pairing_duration"].keys():
                    pairing_profile_menu._text[5] = "No pairing records found."

            else:
                pairing_profile_menu._text = ["No Rat profiles found.",
                                              "Add a Rat to proceed.",
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE]

    def change_pairing_profile(value, *args):
        if pairing_selector_type.get_value()[0] == "Mouse":
            change_mouse(value)
        else:
            change_rat(value)

    def pairing_menu_fork():
        pairing_profile_menu._open(pairing_selector_type._elements[pairing_selector_type._index][1])

    # Pairing Mouse Parameter Menu
    def update_pairing_mouse_start_menu(*args):
        input_data = pairing_mouse_parameter_menu.get_input_data()
        for key in input_data.keys():
            CONFIG["settings"]["pairing_mouse"][key] = input_data[key]

        pairing_mouse_start_menu._text = \
            ['Number of trials: {0}'.format(CONFIG["settings"]["pairing_mouse"]["trial_number"]),
             'Trial length: {0}s'.format(CONFIG["settings"]["pairing_mouse"]["trial_length"]),
             'Inter-Trial length: {0}s'.format(CONFIG["settings"]["pairing_mouse"]["inter_trial_length"]),
             'Speed multiplier: {0}x'.format(CONFIG["settings"]["pairing_mouse"]["speed_multiplier"]),
             'Rel. prob. Blocked: {0}'.format(CONFIG["settings"]["pairing_mouse"]["rel_prob_blocked"]),
             'Rel. prob. Visual: {0}'.format(CONFIG["settings"]["pairing_mouse"]["rel_prob_visual"]),
             'Rel. prob. Smell: {0}'.format(CONFIG["settings"]["pairing_mouse"]["rel_prob_smell"]),
             'Rel. prob. Opened: {0}'.format(CONFIG["settings"]["pairing_mouse"]["rel_prob_opened"])]

    # Pairing Rat Parameter Menu
    def update_pairing_rat_start_menu(*args):
        input_data = pairing_rat_parameter_menu.get_input_data()
        for key in input_data.keys():
            CONFIG["settings"]["pairing_rat"][key] = input_data[key]

        pairing_rat_start_menu._text = \
            ['Number of trials: {0}'.format(CONFIG["settings"]["pairing_rat"]["trial_number"]),
             'Trial length: {0}s'.format(CONFIG["settings"]["pairing_rat"]["trial_length"]),
             'Inter-Trial length: {0}s'.format(CONFIG["settings"]["pairing_rat"]["inter_trial_length"]),
             'Reward timer: {0}'.format(CONFIG["settings"]["pairing_rat"]["reward_timer"]),
             'Speed multiplier: {0}x'.format(CONFIG["settings"]["pairing_rat"]["speed_multiplier"]),
             'Rel. prob. Blocked: {0}'.format(CONFIG["settings"]["pairing_rat"]["rel_prob_blocked"]),
             'Rel. prob. Visual: {0}'.format(CONFIG["settings"]["pairing_rat"]["rel_prob_visual"]),
             'Rel. prob. Smell: {0}'.format(CONFIG["settings"]["pairing_rat"]["rel_prob_smell"]),
             'Rel. prob. Opened: {0}'.format(CONFIG["settings"]["pairing_rat"]["rel_prob_opened"])]

    # Setup Settings Menu
    def update_setup_settings_menu(*args):
        input_data = setup_settings_menu.get_input_data()
        for key in input_data.keys():
            CONFIG["settings"]["setup"][key] = input_data[key]

    # Hardware Settings Menu
    # Lists for the hardware menu
    pwm_0_list = [('12', 18), ('32', 12)]
    pwm_1_list = [('33', 13)]
    gpio_list = [('7', 4), ('8', 14), ('10', 15), ('11', 17), ('13', 27), ('15', 22), ('16', 23), ('18', 24),
                 ('19', 10), ('21', 9), ('22', 25), ('23', 11), ('24', 8), ('26', 7), ('29', 5), ('31', 6), ('35', 19),
                 ('36', 16), ('37', 26), ('38', 20), ('40', 21)]

    # Memory for the hardware menu indexes
    index_memory = {
        "disk_out": [i for i, x in enumerate(pwm_0_list) if x[1] == CONFIG["settings"]["hardware"]["disk_out"]][0],
        "tube_out": [i for i, x in enumerate(pwm_1_list) if x[1] == CONFIG["settings"]["hardware"]["tube_out"]][0],
        "mouse_lick_in":
            [i for i, x in enumerate(gpio_list) if x[1] == CONFIG["settings"]["hardware"]["mouse_lick_in"]][0],
        "mouse_lick_out":
            [i for i, x in enumerate(gpio_list) if x[1] == CONFIG["settings"]["hardware"]["mouse_lick_out"]][0],
        "rat_lick_in": [i for i, x in enumerate(gpio_list) if x[1] == CONFIG["settings"]["hardware"]["rat_lick_in"]][0],
        "rat_lick_out": [i for i, x in enumerate(gpio_list) if x[1] == CONFIG["settings"]["hardware"]["rat_lick_out"]][
            0]
    }

    def update_hardware_settings_menu(*args):
        input_data = hardware_settings_menu.get_input_data()
        for input_key in input_data.keys():
            corresponding_widget = hardware_settings_menu.get_widget(input_key)
            if corresponding_widget != None and corresponding_widget.selected:
                del input_data[input_key]
                if corresponding_widget._index > index_memory[input_key] and \
                        (corresponding_widget._index - index_memory[input_key]) != 20 or \
                        (corresponding_widget._index - index_memory[input_key]) == -20:
                    while corresponding_widget.get_value() in input_data.values():
                        corresponding_widget._index = (corresponding_widget._index + 1) % 21
                else:
                    while corresponding_widget.get_value() in input_data.values():
                        corresponding_widget._index = (corresponding_widget._index - 1) % 21
                index_memory[input_key] = corresponding_widget._index
                CONFIG["settings"]["hardware"][input_key] = \
                    corresponding_widget._elements[corresponding_widget._index][1]
                break

    # Advanced Settings Menu
    def update_advanced_settings_menu(*args):
        input_data = advanced_settings_menu.get_input_data()
        for key in input_data.keys():
            CONFIG["settings"]["advanced"][key] = input_data[key]

    # Mouse Menu
    def change_mouse(value, *args):
        selected, index = value
        if selected == "None":
            return
        global CURRENT_MOUSE
        global MOUSE_NR
        global MOUSE_INFO
        MOUSE_NR = index
        CURRENT_MOUSE = selected
        MOUSE_INFO = ['Name: {0}'.format(CONFIG["mice"][CURRENT_MOUSE]["name"]),
                      'Date of Birth: {0}'.format(CONFIG["mice"][CURRENT_MOUSE]["dob"]),
                      'Starting Weight: {0}g'.format(CONFIG["mice"][CURRENT_MOUSE]["weight"])]
        experiment_selector_mouse._index = index
        experiment_profile_menu._text = \
            [item for sublist in [
                MOUSE_INFO,
                [pygameMenu.locals.TEXT_NEWLINE,
                 pygameMenu.locals.TEXT_NEWLINE,
                 pygameMenu.locals.TEXT_NEWLINE,
                 pygameMenu.locals.TEXT_NEWLINE,
                 pygameMenu.locals.TEXT_NEWLINE]
            ] for item in sublist]
        if not CONFIG["mice"][CURRENT_MOUSE]["performance"].keys():
            experiment_profile_menu._text[5] = "No performance records found."
        elif all(parser.parse(date, dayfirst=True) < datetime.datetime.today() - datetime.timedelta(days=14)
                 for date in CONFIG["mice"][CURRENT_MOUSE]["performance"].keys()):
            experiment_profile_menu._text[5] = "Performance records older than 14 days."
        if pairing_selector_type.get_value()[0] == "Mouse":
            pairing_selector_profile._index = MOUSE_NR
            pairing_profile_menu._text = \
                [item for sublist in [
                    MOUSE_INFO,
                    [pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE]
                ] for item in sublist]
            if not CONFIG["mice"][CURRENT_MOUSE]["pairing_duration"].keys():
                pairing_profile_menu._text[5] = "No pairing records found."
        mouse_selector._index = index
        mouse_menu._text = MOUSE_INFO
        remove_mouse_menu._text = \
            [item for sublist in [
                ["Are you sure you want to remove this Mouse?",
                 pygameMenu.locals.TEXT_NEWLINE,
                 'ID: {0}'.format(CURRENT_MOUSE)],
                MOUSE_INFO
            ] for item in sublist]

    # Add Mouse Menu
    def add_mouse():
        global CONFIG
        data = add_mouse_menu.get_input_data()
        CONFIG["mice"][data["id"]] = dict()
        CONFIG["mice"][data["id"]]["name"] = data["name"]
        raw_date = str(data["dob"])
        CONFIG["mice"][data["id"]]["dob"] = datetime.date(int(raw_date[-4:]), int(raw_date[-6:-4]), int(raw_date[:-6]))
        CONFIG["mice"][data["id"]]["weight"] = data["weight"]
        CONFIG["mice"][data["id"]]["performance"] = dict()
        CONFIG["mice"][data["id"]]["pairing_duration"] = dict()
        with open('config.json', 'w') as outfile:
            json.dump(CONFIG, outfile, indent=4, default=str)

        global CURRENT_MOUSE
        global MOUSE_NR
        global MOUSE_INFO

        if len(CONFIG["mice"]) == 1:
            CURRENT_MOUSE = list(CONFIG["mice"].keys())[0]
        else:
            MOUSE_NR = len(CONFIG["mice"]) - 1
            CURRENT_MOUSE = list(CONFIG["mice"].keys())[MOUSE_NR]

        MOUSE_INFO = ['Name: {0}'.format(CONFIG["mice"][CURRENT_MOUSE]["name"]),
                      'Date of Birth: {0}'.format(CONFIG["mice"][CURRENT_MOUSE]["dob"]),
                      'Starting Weight: {0}g'.format(CONFIG["mice"][CURRENT_MOUSE]["weight"])]
        experiment_selector_mouse.update_elements([(val, CONFIG["mice"][val]["name"])
                                                   for val in list(CONFIG["mice"].keys())])
        experiment_selector_mouse._index = MOUSE_NR
        experiment_profile_menu._text = \
            [item for sublist in [
                MOUSE_INFO,
                [pygameMenu.locals.TEXT_NEWLINE,
                 pygameMenu.locals.TEXT_NEWLINE,
                 pygameMenu.locals.TEXT_NEWLINE,
                 pygameMenu.locals.TEXT_NEWLINE,
                 pygameMenu.locals.TEXT_NEWLINE]
            ] for item in sublist]
        if not CONFIG["mice"][CURRENT_MOUSE]["performance"].keys():
            experiment_profile_menu._text[5] = "No performance records found."
        elif all(parser.parse(date, dayfirst=True) < datetime.datetime.today() - datetime.timedelta(days=14)
                 for date in CONFIG["mice"][CURRENT_MOUSE]["performance"].keys()):
            experiment_profile_menu._text[5] = "Performance records older than 14 days."

        if pairing_selector_type.get_value()[0] == "Mouse":
            pairing_selector_profile.update_elements([(val, CONFIG["mice"][val]["name"]) for val in
                                                      list(CONFIG["mice"].keys())])
            pairing_selector_profile._index = MOUSE_NR
            pairing_profile_menu._text = \
                [item for sublist in [
                    MOUSE_INFO,
                    [pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE]
                ] for item in sublist]
            if not CONFIG["mice"][CURRENT_MOUSE]["pairing_duration"].keys():
                pairing_profile_menu._text[5] = "No pairing records found."
        mouse_selector.update_elements([(val, CONFIG["mice"][val]["name"]) for val in list(CONFIG["mice"].keys())])
        mouse_selector._index = MOUSE_NR
        mouse_menu._text = MOUSE_INFO
        remove_mouse_menu._text = \
            [item for sublist in [
                ["Are you sure you want to remove this Mouse?",
                 pygameMenu.locals.TEXT_NEWLINE,
                 'ID: {0}'.format(CURRENT_MOUSE)],
                MOUSE_INFO
            ] for item in sublist]

        global MESSAGE_TIMERS
        MESSAGE_TIMERS["Mouse added."] = time.time() + message_duration
        add_mouse_menu.reset(1)

    # Remove Mouse Menu
    def remove_mouse():
        global CONFIG
        global MESSAGE_TIMERS

        if len(CONFIG["mice"]) == 0:
            MESSAGE_TIMERS["No mouse found."] = time.time() + message_duration
            return

        global CURRENT_MOUSE
        global MOUSE_NR
        global MOUSE_INFO

        CONFIG["mice"].pop(CURRENT_MOUSE, None)
        with open('config.json', 'w') as outfile:
            json.dump(CONFIG, outfile, indent=4, default=str)

        if len(CONFIG["mice"]) > 0:
            MOUSE_NR = 0
            CURRENT_MOUSE = list(CONFIG["mice"].keys())[MOUSE_NR]
            MOUSE_INFO = ['Name: {0}'.format(CONFIG["mice"][CURRENT_MOUSE]["name"]),
                          'Date of Birth: {0}'.format(CONFIG["mice"][CURRENT_MOUSE]["dob"]),
                          'Starting Weight: {0}g'.format(CONFIG["mice"][CURRENT_MOUSE]["weight"])]
            experiment_selector_mouse._elements = [(val, CONFIG["mice"][val]["name"]) for val in
                                                   list(CONFIG["mice"].keys())]
            experiment_selector_mouse._index = MOUSE_NR
            experiment_profile_menu._text = \
                [item for sublist in [
                    MOUSE_INFO,
                    [pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE]
                ] for item in sublist]
            if not CONFIG["mice"][CURRENT_MOUSE]["performance"].keys():
                experiment_profile_menu._text[5] = "No performance records found."
            elif all(parser.parse(date, dayfirst=True) < datetime.datetime.today() - datetime.timedelta(days=14)
                     for date in CONFIG["mice"][CURRENT_MOUSE]["performance"].keys()):
                experiment_profile_menu._text[5] = "Performance records older than 14 days."

            if pairing_selector_type.get_value()[0] == "Mouse":
                pairing_selector_profile._elements = [(val, CONFIG["mice"][val]["name"]) for val in
                                                      list(CONFIG["mice"].keys())]
                pairing_selector_profile._index = MOUSE_NR
                pairing_profile_menu._text = \
                    [item for sublist in [
                        MOUSE_INFO,
                        [pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE]
                    ] for item in sublist]
                if not CONFIG["mice"][CURRENT_MOUSE]["pairing_duration"].keys():
                    pairing_profile_menu._text[5] = "No pairing records found."
            mouse_selector._elements = [(val, CONFIG["mice"][val]["name"]) for val in list(CONFIG["mice"].keys())]
            mouse_selector._index = MOUSE_NR
            mouse_menu._text = MOUSE_INFO
            remove_mouse_menu._text = \
                [item for sublist in [
                    ["Are you sure you want to remove this Mouse?",
                     pygameMenu.locals.TEXT_NEWLINE,
                     'ID: {0}'.format(CURRENT_MOUSE)],
                    MOUSE_INFO
                ] for item in sublist]
        else:
            MOUSE_NR = 0
            CURRENT_MOUSE = None
            experiment_selector_mouse._elements = [("None", 0)]
            experiment_profile_menu._text = ["No Mouse profiles found.",
                                             "Add a Mouse to proceed.",
                                             pygameMenu.locals.TEXT_NEWLINE,
                                             pygameMenu.locals.TEXT_NEWLINE,
                                             pygameMenu.locals.TEXT_NEWLINE,
                                             pygameMenu.locals.TEXT_NEWLINE,
                                             pygameMenu.locals.TEXT_NEWLINE,
                                             pygameMenu.locals.TEXT_NEWLINE]
            if pairing_selector_type.get_value()[0] == "Mouse":
                pairing_selector_profile._elements = [("None", 0)]
                pairing_profile_menu._text = ["No Mouse profiles found.",
                                              "Add a Mouse to proceed.",
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE]
            mouse_selector._elements = [("None", 0)]
            mouse_menu._text = ["No Mouse profiles found.",
                                "Add a Mouse to proceed.",
                                pygameMenu.locals.TEXT_NEWLINE]
            remove_mouse_menu._text = [pygameMenu.locals.TEXT_NEWLINE,
                                       pygameMenu.locals.TEXT_NEWLINE,
                                       "No Mouse profiles found.",
                                       "Add a Mouse to proceed.",
                                       pygameMenu.locals.TEXT_NEWLINE,
                                       pygameMenu.locals.TEXT_NEWLINE]

        MESSAGE_TIMERS["Mouse removed."] = time.time() + message_duration
        remove_mouse_menu.reset(1)

    # Rat Menu
    def change_rat(value, *args):
        selected, index = value
        if selected == "None":
            return
        global CURRENT_RAT
        global RAT_NR
        global RAT_INFO
        RAT_NR = index
        CURRENT_RAT = selected
        RAT_INFO = ['Name: {0}'.format(CONFIG["rats"][CURRENT_RAT]["name"]),
                    'Date of Birth: {0}'.format(CONFIG["rats"][CURRENT_RAT]["dob"]),
                    'Starting Weight: {0}g'.format(CONFIG["rats"][CURRENT_RAT]["weight"])]
        experiment_selector_rat._index = index
        if pairing_selector_type.get_value()[0] == "Rat":
            pairing_selector_profile._index = RAT_NR
            pairing_profile_menu._text = \
                [item for sublist in [
                    RAT_INFO,
                    [pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE]
                ] for item in sublist]
            if not CONFIG["rats"][CURRENT_RAT]["pairing_duration"].keys():
                pairing_profile_menu._text[5] = "No pairing records found."
        rat_selector._index = index
        rat_menu._text = RAT_INFO
        remove_rat_menu._text = \
            [item for sublist in [
                ["Are you sure you want to remove this Rat?",
                 pygameMenu.locals.TEXT_NEWLINE,
                 'ID: {0}'.format(CURRENT_RAT)],
                RAT_INFO
            ] for item in sublist]

    # Add Rat Menu
    def add_rat():
        global CONFIG
        data = add_rat_menu.get_input_data()
        CONFIG["rats"][data["id"]] = dict()
        CONFIG["rats"][data["id"]]["name"] = data["name"]
        raw_date = str(data["dob"])
        CONFIG["rats"][data["id"]]["dob"] = datetime.date(int(raw_date[-4:]), int(raw_date[-6:-4]), int(raw_date[:-6]))
        CONFIG["rats"][data["id"]]["weight"] = data["weight"]
        CONFIG["rats"][data["id"]]["pairing_duration"] = dict()
        with open('config.json', 'w') as outfile:
            json.dump(CONFIG, outfile, indent=4, default=str)

        global CURRENT_RAT
        global RAT_NR
        global RAT_INFO

        if len(CONFIG["rats"]) == 1:
            CURRENT_RAT = list(CONFIG["rats"].keys())[0]
        else:
            RAT_NR = len(CONFIG["rats"]) - 1
            CURRENT_RAT = list(CONFIG["rats"].keys())[RAT_NR]

        RAT_INFO = ['Name: {0}'.format(CONFIG["rats"][CURRENT_RAT]["name"]),
                    'Date of Birth: {0}'.format(CONFIG["rats"][CURRENT_RAT]["dob"]),
                    'Starting Weight: {0}g'.format(CONFIG["rats"][CURRENT_RAT]["weight"])]
        experiment_selector_rat._elements = [(val, CONFIG["rats"][val]["name"]) for val in list(CONFIG["rats"].keys())]
        experiment_selector_rat._index = RAT_NR
        if pairing_selector_type.get_value()[0] == "Rat":
            pairing_selector_profile._elements = [(val, CONFIG["rats"][val]["name"]) for val in
                                                  list(CONFIG["rats"].keys())]
            pairing_selector_profile._index = RAT_NR
            pairing_profile_menu._text = \
                [item for sublist in [
                    RAT_INFO,
                    [pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE,
                     pygameMenu.locals.TEXT_NEWLINE]
                ] for item in sublist]
            if not CONFIG["rats"][CURRENT_RAT]["pairing_duration"].keys():
                pairing_profile_menu._text[5] = "No pairing records found."
        rat_selector._elements = [(val, CONFIG["rats"][val]["name"]) for val in list(CONFIG["rats"].keys())]
        rat_selector._index = RAT_NR
        rat_menu._text = RAT_INFO
        remove_rat_menu._text = \
            [item for sublist in [
                ["Are you sure you want to remove this Rat?",
                 pygameMenu.locals.TEXT_NEWLINE,
                 'ID: {0}'.format(CURRENT_RAT)],
                RAT_INFO
            ] for item in sublist]

        global MESSAGE_TIMERS
        MESSAGE_TIMERS["Rat added."] = time.time() + message_duration
        add_rat_menu.reset(1)

    # Remove Rat Menu
    def remove_rat():
        global CONFIG
        global MESSAGE_TIMERS

        if len(CONFIG["rats"]) == 0:
            MESSAGE_TIMERS["No Rat found."] = time.time() + message_duration
            return

        global CURRENT_RAT
        global RAT_NR
        global RAT_INFO

        CONFIG["rats"].pop(CURRENT_RAT, None)
        with open('config.json', 'w') as outfile:
            json.dump(CONFIG, outfile, indent=4, default=str)

        if len(CONFIG["rats"]) > 0:
            RAT_NR = 0
            CURRENT_RAT = list(CONFIG["rats"].keys())[RAT_NR]
            RAT_INFO = ['Name: {0}'.format(CONFIG["rats"][CURRENT_RAT]["name"]),
                        'Date of Birth: {0}'.format(CONFIG["rats"][CURRENT_RAT]["dob"]),
                        'Starting Weight: {0}g'.format(config["rats"][CURRENT_RAT]["weight"])]
            experiment_selector_rat._elements = [(val, config["rats"][val]["name"]) for val in
                                                 list(config["rats"].keys())]
            experiment_selector_rat._index = RAT_NR
            if pairing_selector_type.get_value()[0] == "Rat":
                pairing_selector_profile._elements = [(val, config["rats"][val]["name"]) for val in
                                                      list(config["rats"].keys())]
                pairing_selector_profile._index = RAT_NR
                pairing_profile_menu._text = \
                    [item for sublist in [
                        RAT_INFO,
                        [pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE,
                         pygameMenu.locals.TEXT_NEWLINE]
                    ] for item in sublist]
                if not config["rats"][CURRENT_MOUSE]["pairing_duration"].keys():
                    pairing_profile_menu._text[5] = "No pairing records found."
            rat_selector._elements = [(val, config["rats"][val]["name"]) for val in list(config["rats"].keys())]
            rat_selector._index = RAT_NR
            rat_menu._text = RAT_INFO
            remove_rat_menu._text = \
                [item for sublist in [
                    ["Are you sure you want to remove this Rat?",
                     pygameMenu.locals.TEXT_NEWLINE,
                     'ID: {0}'.format(CURRENT_RAT)],
                    RAT_INFO
                ] for item in sublist]
        else:
            RAT_NR = 0
            CURRENT_RAT = None
            experiment_selector_rat._elements = [("None", 0)]
            if pairing_selector_type.get_value()[0] == "Rat":
                pairing_selector_profile._elements = [("None", 0)]
                pairing_profile_menu._text = ["No Rat profiles found.",
                                              "Add a Rat to proceed.",
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE,
                                              pygameMenu.locals.TEXT_NEWLINE]
            rat_selector._elements = [("None", 0)]
            rat_menu._text = ["No Rat profiles found.",
                              "Add a Rat to proceed.",
                              pygameMenu.locals.TEXT_NEWLINE]
            remove_rat_menu._text = [pygameMenu.locals.TEXT_NEWLINE,
                                     pygameMenu.locals.TEXT_NEWLINE,
                                     "No Rat profiles found.",
                                     "Add a Rat to proceed.",
                                     pygameMenu.locals.TEXT_NEWLINE,
                                     pygameMenu.locals.TEXT_NEWLINE]

        MESSAGE_TIMERS["Rat removed."] = time.time() + message_duration
        remove_rat_menu.reset(1)

    # -------------------------------------------------------------------------
    # Link menus and add options
    # -------------------------------------------------------------------------
    # Are there profiles?
    if len(CONFIG["rats"]) > 0:
        CURRENT_RAT = list(CONFIG["rats"].keys())[RAT_NR]
        RAT_INFO = ['Name: {0}'.format(CONFIG["rats"][CURRENT_RAT]["name"]),
                    'Date of Birth: {0}'.format(CONFIG["rats"][CURRENT_RAT]["dob"]),
                    'Starting Weight: {0}g'.format(CONFIG["rats"][CURRENT_RAT]["weight"])]
        rat_selector_list = [(val, CONFIG["rats"][val]["name"]) for val in list(CONFIG["rats"].keys())]
        for m in RAT_INFO:
            rat_menu.add_line(m)
        remove_rat_menu.add_line("Are you sure you want to remove this Rat?")
        remove_rat_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        remove_rat_menu.add_line('ID: {0}'.format(CURRENT_RAT))
        for m in RAT_INFO:
            remove_rat_menu.add_line(m)

    else:
        rat_selector_list = [("None", 0)]
        rat_menu.add_line("No Rat profiles found.")
        rat_menu.add_line("Add a Rat to proceed.")
        rat_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        remove_rat_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        remove_rat_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        remove_rat_menu.add_line("No Rat profiles found.")
        remove_rat_menu.add_line("Add a Rat to proceed.")
        remove_rat_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        remove_rat_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)

    if len(CONFIG["mice"]) > 0:
        CURRENT_MOUSE = list(CONFIG["mice"].keys())[MOUSE_NR]
        MOUSE_INFO = ['Name: {0}'.format(CONFIG["mice"][CURRENT_MOUSE]["name"]),
                      'Date of Birth: {0}'.format(CONFIG["mice"][CURRENT_MOUSE]["dob"]),
                      'Starting Weight: {0}g'.format(CONFIG["mice"][CURRENT_MOUSE]["weight"])]
        mouse_selector_list = [(val, CONFIG["mice"][val]["name"]) for val in list(CONFIG["mice"].keys())]
        for m in MOUSE_INFO:
            experiment_profile_menu.add_line(m)
            pairing_profile_menu.add_line(m)
            mouse_menu.add_line(m)
        experiment_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        experiment_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        experiment_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        experiment_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        experiment_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        if not CONFIG["mice"][CURRENT_MOUSE]["performance"].keys():
            experiment_profile_menu._text[5] = "No performance records found."
        elif all(parser.parse(date, dayfirst=True) < datetime.datetime.today() - datetime.timedelta(days=14)
                 for date in CONFIG["mice"][CURRENT_MOUSE]["performance"].keys()):
            experiment_profile_menu._text[5] = "Performance records older than 14 days."

        if not CONFIG["mice"][CURRENT_MOUSE]["pairing_duration"].keys():
            pairing_profile_menu._text[5] = "No pairing records found."
        pairing_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        pairing_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        pairing_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        pairing_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        pairing_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        remove_mouse_menu.add_line("Are you sure you want to remove this Mouse?")
        remove_mouse_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        remove_mouse_menu.add_line('ID: {0}'.format(CURRENT_MOUSE))
        for m in MOUSE_INFO:
            remove_mouse_menu.add_line(m)

    else:
        mouse_selector_list = [("None", 0)]
        experiment_profile_menu.add_line("No Mouse profiles found.")
        experiment_profile_menu.add_line("Add a Mouse to proceed.")
        experiment_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        experiment_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        experiment_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        experiment_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        experiment_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        experiment_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        pairing_profile_menu.add_line("No Mouse profiles found.")
        pairing_profile_menu.add_line("Add a Mouse to proceed.")
        pairing_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        pairing_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        pairing_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        pairing_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        pairing_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        pairing_profile_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        mouse_menu.add_line("No Mouse profiles found.")
        mouse_menu.add_line("Add a Mouse to proceed.")
        mouse_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        remove_mouse_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        remove_mouse_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        remove_mouse_menu.add_line("No Mouse profiles found.")
        remove_mouse_menu.add_line("Add a Mouse to proceed.")
        remove_mouse_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
        remove_mouse_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)

    # Main Menu
    main_menu.add_selector('',
                           [("Run Experiment", experiment_profile_menu), ("Run Pairing", pairing_profile_menu)],
                           selector_id='experiment_pairing_select',
                           default=MOUSE_NR,
                           onreturn=main_menu_fork)
    main_menu.add_selector('',
                           [("Mouse Profiles", mouse_menu), ("Rat Profiles", rat_menu)],
                           selector_id='mouse_rat_profiles',
                           default=MOUSE_NR,
                           onreturn=main_menu_fork)
    main_menu.add_option('Settings', settings_menu)
    main_menu.add_option('About', about_menu)
    main_menu.add_option('Quit', pygameMenu.events.EXIT)
    main_menu.set_fps(FPS)

    MAIN_MENUBAR = main_menu._menubar

    # Experiment Profile Menu
    experiment_selector_mouse = experiment_profile_menu.add_selector('Mouse: ',
                                                                     mouse_selector_list,
                                                                     selector_id='mouse_experiment',
                                                                     default=MOUSE_NR,
                                                                     onchange=change_mouse)
    experiment_selector_rat = experiment_profile_menu.add_selector('Rat: ',
                                                                   rat_selector_list,
                                                                   selector_id='rat_experiment',
                                                                   default=RAT_NR,
                                                                   onchange=change_rat)
    experiment_profile_menu.add_option('Go to start menu', experiment_start_menu)
    experiment_profile_menu.add_option('Return to main menu', pygameMenu.events.BACK)

    EXPERIMENT_MENUBAR = experiment_profile_menu._menubar

    # Experiment Start Menu
    start_menu_text = \
        ['Run a virtual experiment?: {0}'.format("Yes" if VIRTUAL_EXPERIMENT else "No"),
         'Number of trials: {0}'.format(CONFIG["settings"]["experiment"]["trial_number"]),
         'Trial length: {0}s'.format(CONFIG["settings"]["experiment"]["trial_length"]),
         'Inter-Trial length: {0}s'.format(CONFIG["settings"]["experiment"]["inter_trial_length"]),
         'Reward length: {0}s'.format(CONFIG["settings"]["experiment"]["reward_length"]),
         'Reward timer for rat: {0}s'.format(CONFIG["settings"]["experiment"]["reward_timer_rat"]),
         'Speed multiplier: {0}s'.format(CONFIG["settings"]["experiment"]["speed_multiplier"]),
         'Rel. prob. Blocked: {0}'.format(CONFIG["settings"]["experiment"]["rel_prob_blocked"]),
         'Rel. prob. Visual: {0}'.format(CONFIG["settings"]["experiment"]["rel_prob_visual"]),
         'Rel. prob. Smell: {0}'.format(CONFIG["settings"]["experiment"]["rel_prob_smell"]),
         'Rel. prob. Opened: {0}'.format(CONFIG["settings"]["experiment"]["rel_prob_opened"])]
    for line in start_menu_text:
        experiment_start_menu.add_line(line)
    experiment_start_menu.add_option('Start Experiment', experiment_loop)
    experiment_start_menu.add_option('Change parameters', experiment_parameter_menu)
    experiment_start_menu.add_option('Return to profiles', pygameMenu.events.BACK)

    # Experiment Parameter Menu
    experiment_parameter_menu.add_selector('Run a virtual experiment?: ',
                                           [("No", False), ("Yes", True)],
                                           selector_id='virtual_experiment',
                                           default=0,
                                           onchange=update_experiment_start_menu)
    experiment_parameter_menu.add_text_input('Number of trials: ',
                                             maxchar=5,
                                             default=CONFIG["settings"]["experiment"]["trial_number"],
                                             textinput_id='trial_number',
                                             input_type=pygameMenu.locals.INPUT_INT,
                                             onchange=update_experiment_start_menu,
                                             onreturn=save_config,
                                             enable_selection=False)
    experiment_parameter_menu.add_text_input('Trial length: ',
                                             maxchar=2,
                                             default=CONFIG["settings"]["experiment"]["trial_length"],
                                             textinput_id='trial_length',
                                             input_type=pygameMenu.locals.INPUT_INT,
                                             onchange=update_experiment_start_menu,
                                             onreturn=save_config,
                                             enable_selection=False)
    experiment_parameter_menu.add_text_input('Inter-trial length: ',
                                             maxchar=2,
                                             default=CONFIG["settings"]["experiment"]["inter_trial_length"],
                                             textinput_id='inter_trial_length',
                                             input_type=pygameMenu.locals.INPUT_INT,
                                             onchange=update_experiment_start_menu,
                                             onreturn=save_config,
                                             enable_selection=False)
    experiment_parameter_menu.add_text_input('Reward length: ',
                                             maxchar=2,
                                             default=CONFIG["settings"]["experiment"]["reward_length"],
                                             textinput_id='reward_length',
                                             input_type=pygameMenu.locals.INPUT_INT,
                                             onchange=update_experiment_start_menu,
                                             onreturn=save_config,
                                             enable_selection=False)
    experiment_parameter_menu.add_text_input('Reward timer for rat: ',
                                             maxchar=2,
                                             default=CONFIG["settings"]["experiment"]["reward_timer_rat"],
                                             textinput_id='reward_timer_rat',
                                             input_type=pygameMenu.locals.INPUT_INT,
                                             onchange=update_experiment_start_menu,
                                             onreturn=save_config,
                                             enable_selection=False)
    experiment_parameter_menu.add_text_input('Speed multiplier: ',
                                             maxchar=3,
                                             default=CONFIG["settings"]["experiment"]["speed_multiplier"],
                                             textinput_id='speed_multiplier',
                                             input_type=pygameMenu.locals.INPUT_FLOAT,
                                             onchange=update_experiment_start_menu,
                                             onreturn=save_config,
                                             enable_selection=False)
    experiment_parameter_menu.add_text_input('Rel. prob. Blocked: ',
                                             maxchar=3,
                                             default=CONFIG["settings"]["experiment"]["rel_prob_blocked"],
                                             textinput_id='rel_prob_blocked',
                                             input_type=pygameMenu.locals.INPUT_INT,
                                             onchange=update_experiment_start_menu,
                                             onreturn=save_config,
                                             enable_selection=False)
    experiment_parameter_menu.add_text_input('Rel. prob. Visual: ',
                                             maxchar=3,
                                             default=CONFIG["settings"]["experiment"]["rel_prob_visual"],
                                             textinput_id='rel_prob_visual',
                                             input_type=pygameMenu.locals.INPUT_INT,
                                             onchange=update_experiment_start_menu,
                                             onreturn=save_config,
                                             enable_selection=False)
    experiment_parameter_menu.add_text_input('Rel. prob. Smell: ',
                                             maxchar=3,
                                             default=CONFIG["settings"]["experiment"]["rel_prob_smell"],
                                             textinput_id='rel_prob_smell',
                                             input_type=pygameMenu.locals.INPUT_INT,
                                             onchange=update_experiment_start_menu,
                                             onreturn=save_config,
                                             enable_selection=False)
    experiment_parameter_menu.add_text_input('Rel. prob. Opened: ',
                                             maxchar=3,
                                             default=CONFIG["settings"]["experiment"]["rel_prob_opened"],
                                             textinput_id='rel_prob_opened',
                                             input_type=pygameMenu.locals.INPUT_INT,
                                             onchange=update_experiment_start_menu,
                                             onreturn=save_config,
                                             enable_selection=False)
    experiment_parameter_menu.add_option('Return to start menu', pygameMenu.events.BACK)

    # Pairing Profile Menu
    pairing_selector_type = pairing_profile_menu.add_selector('Pairing for ',
                                                              [("Mouse", pairing_mouse_start_menu),
                                                               ("Rat", pairing_rat_start_menu)],
                                                              selector_id='pairing_type',
                                                              default=0,
                                                              onchange=change_pairing_type)
    pairing_selector_profile = pairing_profile_menu.add_selector('Mouse: ',
                                                                 mouse_selector_list,
                                                                 selector_id='pairing_profile',
                                                                 default=MOUSE_NR,
                                                                 onchange=change_pairing_profile)
    pairing_profile_menu.add_option('Go to start menu', pairing_menu_fork)
    pairing_profile_menu.add_option('Return to main menu', pygameMenu.events.BACK)

    PAIRING_MENUBAR = pairing_profile_menu._menubar

    # Pairing Mouse Start Menu
    start_menu_text = \
        ['Number of trials: {0}'.format(CONFIG["settings"]["pairing_mouse"]["trial_number"]),
         'Trial length: {0}s'.format(CONFIG["settings"]["pairing_mouse"]["trial_length"]),
         'Inter-Trial length: {0}s'.format(CONFIG["settings"]["pairing_mouse"]["inter_trial_length"]),
         'Speed multiplier: {0}s'.format(CONFIG["settings"]["pairing_mouse"]["speed_multiplier"]),
         'Rel. prob. Blocked: {0}'.format(CONFIG["settings"]["pairing_mouse"]["rel_prob_blocked"]),
         'Rel. prob. Visual: {0}'.format(CONFIG["settings"]["pairing_mouse"]["rel_prob_visual"]),
         'Rel. prob. Smell: {0}'.format(CONFIG["settings"]["pairing_mouse"]["rel_prob_smell"]),
         'Rel. prob. Opened: {0}'.format(CONFIG["settings"]["pairing_mouse"]["rel_prob_opened"])]
    for line in start_menu_text:
        pairing_mouse_start_menu.add_line(line)
    pairing_mouse_start_menu.add_option('Start Experiment', pairing_mouse_loop)
    pairing_mouse_start_menu.add_option('Change parameters', pairing_mouse_parameter_menu)
    pairing_mouse_start_menu.add_option('Return to profiles', pygameMenu.events.BACK)

    # Pairing Mouse Parameter Menu
    pairing_mouse_parameter_menu.add_text_input('Number of trials: ',
                                                maxchar=5,
                                                default=CONFIG["settings"]["pairing_mouse"]["trial_number"],
                                                textinput_id='trial_number',
                                                input_type=pygameMenu.locals.INPUT_INT,
                                                onchange=update_pairing_mouse_start_menu,
                                                onreturn=save_config,
                                                enable_selection=False)
    pairing_mouse_parameter_menu.add_text_input('Trial length: ',
                                                maxchar=2,
                                                default=CONFIG["settings"]["pairing_mouse"]["trial_length"],
                                                textinput_id='trial_length',
                                                input_type=pygameMenu.locals.INPUT_INT,
                                                onchange=update_pairing_mouse_start_menu,
                                                onreturn=save_config,
                                                enable_selection=False)
    pairing_mouse_parameter_menu.add_text_input('Inter-trial length: ',
                                                maxchar=2,
                                                default=CONFIG["settings"]["pairing_mouse"]["inter_trial_length"],
                                                textinput_id='inter_trial_length',
                                                input_type=pygameMenu.locals.INPUT_INT,
                                                onchange=update_pairing_mouse_start_menu,
                                                onreturn=save_config,
                                                enable_selection=False)
    pairing_mouse_parameter_menu.add_text_input('Speed multiplier: ',
                                                maxchar=3,
                                                default=CONFIG["settings"]["pairing_mouse"]["speed_multiplier"],
                                                textinput_id='speed_multiplier',
                                                input_type=pygameMenu.locals.INPUT_FLOAT,
                                                onchange=update_pairing_mouse_start_menu,
                                                onreturn=save_config,
                                                enable_selection=False)
    pairing_mouse_parameter_menu.add_text_input('Rel. prob. Blocked: ',
                                                maxchar=3,
                                                default=CONFIG["settings"]["pairing_mouse"]["rel_prob_blocked"],
                                                textinput_id='rel_prob_blocked',
                                                input_type=pygameMenu.locals.INPUT_INT,
                                                onchange=update_pairing_mouse_start_menu,
                                                onreturn=save_config,
                                                enable_selection=False)
    pairing_mouse_parameter_menu.add_text_input('Rel. prob. Visual: ',
                                                maxchar=3,
                                                default=CONFIG["settings"]["pairing_mouse"]["rel_prob_visual"],
                                                textinput_id='rel_prob_visual',
                                                input_type=pygameMenu.locals.INPUT_INT,
                                                onchange=update_pairing_mouse_start_menu,
                                                onreturn=save_config,
                                                enable_selection=False)
    pairing_mouse_parameter_menu.add_text_input('Rel. prob. Smell: ',
                                                maxchar=3,
                                                default=CONFIG["settings"]["pairing_mouse"]["rel_prob_smell"],
                                                textinput_id='rel_prob_smell',
                                                input_type=pygameMenu.locals.INPUT_INT,
                                                onchange=update_pairing_mouse_start_menu,
                                                onreturn=save_config,
                                                enable_selection=False)
    pairing_mouse_parameter_menu.add_text_input('Rel. prob. Opened: ',
                                                maxchar=3,
                                                default=CONFIG["settings"]["pairing_mouse"]["rel_prob_opened"],
                                                textinput_id='rel_prob_opened',
                                                input_type=pygameMenu.locals.INPUT_INT,
                                                onchange=update_pairing_mouse_start_menu,
                                                onreturn=save_config,
                                                enable_selection=False)
    pairing_mouse_parameter_menu.add_option('Return to start menu', pygameMenu.events.BACK)

    # Pairing Rat Start Menu
    start_menu_text = \
        ['Number of trials: {0}'.format(CONFIG["settings"]["pairing_rat"]["trial_number"]),
         'Trial length: {0}s'.format(CONFIG["settings"]["pairing_rat"]["trial_length"]),
         'Inter-Trial length: {0}s'.format(CONFIG["settings"]["pairing_rat"]["inter_trial_length"]),
         'Speed multiplier: {0}s'.format(CONFIG["settings"]["pairing_rat"]["speed_multiplier"]),
         'Reward timer: {0}s'.format(CONFIG["settings"]["pairing_rat"]["reward_timer"]),
         'Rel. prob. Blocked: {0}'.format(CONFIG["settings"]["pairing_rat"]["rel_prob_blocked"]),
         'Rel. prob. Visual: {0}'.format(CONFIG["settings"]["pairing_rat"]["rel_prob_visual"]),
         'Rel. prob. Smell: {0}'.format(CONFIG["settings"]["pairing_rat"]["rel_prob_smell"]),
         'Rel. prob. Opened: {0}'.format(CONFIG["settings"]["pairing_rat"]["rel_prob_opened"])]
    for line in start_menu_text:
        pairing_rat_start_menu.add_line(line)
    pairing_rat_start_menu.add_option('Start Experiment', pairing_rat_loop)
    pairing_rat_start_menu.add_option('Change parameters', pairing_rat_parameter_menu)
    pairing_rat_start_menu.add_option('Return to profiles', pygameMenu.events.BACK)

    # Pairing Mouse Parameter Menu
    pairing_rat_parameter_menu.add_text_input('Number of trials: ',
                                              maxchar=5,
                                              default=CONFIG["settings"]["pairing_rat"]["trial_number"],
                                              textinput_id='trial_number',
                                              input_type=pygameMenu.locals.INPUT_INT,
                                              onchange=update_pairing_rat_start_menu,
                                              onreturn=save_config,
                                              enable_selection=False)
    pairing_rat_parameter_menu.add_text_input('Trial length: ',
                                              maxchar=2,
                                              default=CONFIG["settings"]["pairing_rat"]["trial_length"],
                                              textinput_id='trial_length',
                                              input_type=pygameMenu.locals.INPUT_INT,
                                              onchange=update_pairing_rat_start_menu,
                                              onreturn=save_config,
                                              enable_selection=False)
    pairing_rat_parameter_menu.add_text_input('Inter-trial length: ',
                                              maxchar=2,
                                              default=CONFIG["settings"]["pairing_rat"]["inter_trial_length"],
                                              textinput_id='inter_trial_length',
                                              input_type=pygameMenu.locals.INPUT_INT,
                                              onchange=update_pairing_rat_start_menu,
                                              onreturn=save_config,
                                              enable_selection=False)
    pairing_rat_parameter_menu.add_text_input('Reward timer: ',
                                              maxchar=2,
                                              default=CONFIG["settings"]["pairing_rat"]["reward_timer"],
                                              textinput_id='reward_timer',
                                              input_type=pygameMenu.locals.INPUT_INT,
                                              onchange=update_pairing_rat_start_menu,
                                              onreturn=save_config,
                                              enable_selection=False)
    pairing_rat_parameter_menu.add_text_input('Speed multiplier: ',
                                              maxchar=3,
                                              default=CONFIG["settings"]["pairing_rat"]["speed_multiplier"],
                                              textinput_id='speed_multiplier',
                                              input_type=pygameMenu.locals.INPUT_FLOAT,
                                              onchange=update_pairing_rat_start_menu,
                                              onreturn=save_config,
                                              enable_selection=False)
    pairing_rat_parameter_menu.add_text_input('Rel. prob. Blocked: ',
                                              maxchar=3,
                                              default=CONFIG["settings"]["pairing_rat"]["rel_prob_blocked"],
                                              textinput_id='rel_prob_blocked',
                                              input_type=pygameMenu.locals.INPUT_INT,
                                              onchange=update_pairing_rat_start_menu,
                                              onreturn=save_config,
                                              enable_selection=False)
    pairing_rat_parameter_menu.add_text_input('Rel. prob. Visual: ',
                                              maxchar=3,
                                              default=CONFIG["settings"]["pairing_rat"]["rel_prob_visual"],
                                              textinput_id='rel_prob_visual',
                                              input_type=pygameMenu.locals.INPUT_INT,
                                              onchange=update_pairing_rat_start_menu,
                                              onreturn=save_config,
                                              enable_selection=False)
    pairing_rat_parameter_menu.add_text_input('Rel. prob. Smell: ',
                                              maxchar=3,
                                              default=CONFIG["settings"]["pairing_rat"]["rel_prob_smell"],
                                              textinput_id='rel_prob_smell',
                                              input_type=pygameMenu.locals.INPUT_INT,
                                              onchange=update_pairing_rat_start_menu,
                                              onreturn=save_config,
                                              enable_selection=False)
    pairing_rat_parameter_menu.add_text_input('Rel. prob. Opened: ',
                                              maxchar=3,
                                              default=CONFIG["settings"]["pairing_rat"]["rel_prob_opened"],
                                              textinput_id='rel_prob_opened',
                                              input_type=pygameMenu.locals.INPUT_INT,
                                              onchange=update_pairing_rat_start_menu,
                                              onreturn=save_config,
                                              enable_selection=False)
    pairing_rat_parameter_menu.add_option('Return to start menu', pygameMenu.events.BACK)

    # Settings Menu
    settings_menu.add_option('Setup options', setup_settings_menu)
    settings_menu.add_option('Hardware & Pins', hardware_settings_menu)
    settings_menu.add_option('Advanced settings', advanced_settings_menu)
    settings_menu.add_option('Return to main menu', pygameMenu.events.BACK)

    # Setup Settings Menu
    global p_cm_input  # Yes, it is silly to turn that into a global, but it doesnt work any other way
    p_cm_input = setup_settings_menu.add_text_input('Pixel/Centimeter: ',
                                                    maxchar=5,
                                                    default=CONFIG["settings"]["setup"]["p_cm_ratio"],
                                                    textinput_id='p_cm_ratio',
                                                    input_type=pygameMenu.locals.INPUT_FLOAT,
                                                    onchange=update_setup_settings_menu,
                                                    onreturn=save_config,
                                                    enable_selection=False)
    setup_settings_menu.add_text_input('Wheel diameter: ',
                                       maxchar=4,
                                       default=CONFIG["settings"]["setup"]["wheel_diameter"],
                                       textinput_id='wheel_diameter',
                                       input_type=pygameMenu.locals.INPUT_FLOAT,
                                       onchange=update_setup_settings_menu,
                                       onreturn=save_config,
                                       enable_selection=False)
    setup_settings_menu.add_text_input('Tube distance: ',
                                       maxchar=4,
                                       default=CONFIG["settings"]["setup"]["tube_distance"],
                                       textinput_id='tube_distance',
                                       input_type=pygameMenu.locals.INPUT_FLOAT,
                                       onchange=update_setup_settings_menu,
                                       onreturn=save_config,
                                       enable_selection=False)

    setup_settings_menu.add_option('Calibrate Pixel/Centimeter Ratio', calibration_loop)
    setup_settings_menu.add_option('Return to settings menu', pygameMenu.events.BACK)

    # Hardware Settings Menu
    hardware_settings_menu.add_selector('Disk output pin: ',
                                        pwm_0_list,
                                        selector_id='disk_out',
                                        default=index_memory['disk_out'],
                                        onchange=update_hardware_settings_menu,
                                        onreturn=save_config,
                                        align=pygameMenu.locals.ALIGN_LEFT)
    hardware_settings_menu.add_selector('Tube output pin: ',
                                        pwm_1_list,
                                        selector_id='tube_out',
                                        default=index_memory['tube_out'],
                                        onchange=update_hardware_settings_menu,
                                        onreturn=save_config,
                                        align=pygameMenu.locals.ALIGN_LEFT)
    hardware_settings_menu.add_selector('Mouse lick input pin: ',
                                        gpio_list,
                                        selector_id='mouse_lick_in',
                                        default=index_memory['mouse_lick_in'],
                                        onchange=update_hardware_settings_menu,
                                        onreturn=save_config,
                                        align=pygameMenu.locals.ALIGN_LEFT)
    hardware_settings_menu.add_selector('Mouse lick output pin: ',
                                        gpio_list,
                                        selector_id='mouse_lick_out',
                                        default=index_memory['mouse_lick_out'],
                                        onchange=update_hardware_settings_menu,
                                        onreturn=save_config,
                                        align=pygameMenu.locals.ALIGN_LEFT)
    hardware_settings_menu.add_selector('Rat lick input pin: ',
                                        gpio_list,
                                        selector_id='rat_lick_in',
                                        default=index_memory['rat_lick_in'],
                                        onchange=update_hardware_settings_menu,
                                        onreturn=save_config,
                                        align=pygameMenu.locals.ALIGN_LEFT)
    hardware_settings_menu.add_selector('Rat lick output pin: ',
                                        gpio_list,
                                        selector_id='rat_lick_out',
                                        default=index_memory['rat_lick_out'],
                                        onchange=update_hardware_settings_menu,
                                        onreturn=save_config,
                                        align=pygameMenu.locals.ALIGN_LEFT)

    hardware_settings_menu.add_option('Return to settings menu', pygameMenu.events.BACK,
                                      align=pygameMenu.locals.ALIGN_CENTER)

    HARDWARE_MENUBAR = hardware_settings_menu._menubar

    # Advanced Settings Menu
    advanced_settings_menu.add_text_input('Message duration: ',
                                          maxchar=2,
                                          default=CONFIG["settings"]["advanced"]["message_duration"],
                                          textinput_id='message_duration',
                                          input_type=pygameMenu.locals.INPUT_INT,
                                          onchange=update_advanced_settings_menu,
                                          onreturn=save_config,
                                          enable_selection=False)
    advanced_settings_menu.add_text_input('Font name: ',
                                          maxchar=2,
                                          default=CONFIG["settings"]["advanced"]["font_name"],
                                          textinput_id='font_name',
                                          input_type=pygameMenu.locals.INPUT_TEXT,
                                          onchange=update_advanced_settings_menu,
                                          onreturn=save_config,
                                          enable_selection=False)
    advanced_settings_menu.add_text_input('Acceleration cutoff: ',
                                          maxchar=3,
                                          default=CONFIG["settings"]["advanced"]["acceleration_cutoff"],
                                          textinput_id='acceleration_cutoff',
                                          input_type=pygameMenu.locals.INPUT_FLOAT,
                                          onchange=update_advanced_settings_menu,
                                          onreturn=save_config,
                                          enable_selection=False)
    advanced_settings_menu.add_text_input('Reward abort at: ',
                                          maxchar=2,
                                          default=CONFIG["settings"]["advanced"]["reward_abort"],
                                          textinput_id='reward_abort',
                                          input_type=pygameMenu.locals.INPUT_FLOAT,
                                          onchange=update_advanced_settings_menu,
                                          onreturn=save_config,
                                          enable_selection=False)
    advanced_settings_menu.add_text_input('Marker height: ',
                                          maxchar=3,
                                          default=CONFIG["settings"]["advanced"]["marker_height"],
                                          textinput_id='marker_height',
                                          input_type=pygameMenu.locals.INPUT_INT,
                                          onchange=update_advanced_settings_menu,
                                          onreturn=save_config,
                                          enable_selection=False)

    advanced_settings_menu.add_option('Return to settings menu', pygameMenu.events.BACK)

    # Mouse Menu
    mouse_selector = mouse_menu.add_selector('Profile: ',
                                             mouse_selector_list,
                                             selector_id='mouse_profiles',
                                             default=MOUSE_NR,
                                             onchange=change_mouse)

    mouse_menu.add_option('Add Mouse', add_mouse_menu)
    mouse_menu.add_option('Remove Mouse', remove_mouse_menu)
    mouse_menu.add_option('Return to main menu', pygameMenu.events.BACK)

    # Add Mouse Menu
    add_mouse_menu.add_text_input('Nickname: ',
                                  maxchar=20,
                                  textinput_id='name',
                                  input_underline='_',
                                  align=pygameMenu.locals.ALIGN_LEFT)
    add_mouse_menu.add_text_input('Mouse-ID: ',
                                  maxchar=20,
                                  textinput_id='id',
                                  input_underline='_',
                                  align=pygameMenu.locals.ALIGN_LEFT)
    add_mouse_menu.add_text_input('Date of Birth (DDMMYYYY): ',
                                  maxchar=8,
                                  textinput_id='dob',
                                  input_type=pygameMenu.locals.INPUT_INT,
                                  input_underline='_',
                                  align=pygameMenu.locals.ALIGN_LEFT)
    add_mouse_menu.add_text_input('Original Weight (in gram): ',
                                  maxchar=7,
                                  textinput_id='weight',
                                  input_type=pygameMenu.locals.INPUT_INT,
                                  input_underline='_',
                                  align=pygameMenu.locals.ALIGN_LEFT)

    add_mouse_menu.add_option('Confirm', add_mouse)
    add_mouse_menu.add_option('Cancel', pygameMenu.events.BACK)

    # Remove Mouse Menu
    remove_mouse_menu.add_option('Confirm', remove_mouse)
    remove_mouse_menu.add_option('Cancel', pygameMenu.events.BACK)

    # Rat Menu
    rat_selector = rat_menu.add_selector('Profile: ',
                                         rat_selector_list,
                                         selector_id='rat_profiles',
                                         default=RAT_NR,
                                         onchange=change_rat)

    rat_menu.add_option('Add Rat', add_rat_menu)
    rat_menu.add_option('Remove Rat', remove_rat_menu)
    rat_menu.add_option('Return to main menu', pygameMenu.events.BACK)

    # Add Rat Menu
    add_rat_menu.add_text_input('Nickname: ',
                                maxchar=20,
                                textinput_id='name',
                                input_underline='_',
                                align=pygameMenu.locals.ALIGN_LEFT)
    add_rat_menu.add_text_input('Rat-ID: ',
                                maxchar=20,
                                textinput_id='id',
                                input_underline='_',
                                align=pygameMenu.locals.ALIGN_LEFT)
    add_rat_menu.add_text_input('Date of Birth (DDMMYYYY): ',
                                maxchar=8,
                                textinput_id='dob',
                                input_type=pygameMenu.locals.INPUT_INT,
                                input_underline='_',
                                align=pygameMenu.locals.ALIGN_LEFT)
    add_rat_menu.add_text_input('Original Weight (in gram): ',
                                maxchar=7,
                                textinput_id='weight',
                                input_type=pygameMenu.locals.INPUT_INT,
                                input_underline='_',
                                align=pygameMenu.locals.ALIGN_LEFT)

    add_rat_menu.add_option('Confirm', add_rat)
    add_rat_menu.add_option('Cancel', pygameMenu.events.BACK)

    # Remove Rat Menu
    remove_rat_menu.add_option('Confirm', remove_rat)
    remove_rat_menu.add_option('Cancel', pygameMenu.events.BACK)

    # About Menu
    for m in ABOUT:
        about_menu.add_line(m)
    about_menu.add_line(pygameMenu.locals.TEXT_NEWLINE)
    about_menu.add_option('Return to main menu', pygameMenu.events.BACK)

    # -------------------------------------------------------------------------
    # Main loop
    # -------------------------------------------------------------------------
    while True:
        # Tick
        clock.tick(FPS)

        # Paint background
        main_background()

        # Application events
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                exit()

        # Main menu
        main_menu.mainloop(events, disable_loop=test)

        # Flip surface
        pygame.display.flip()

        # At first loop returns
        if test:
            break


if __name__ == '__main__':
    main()
