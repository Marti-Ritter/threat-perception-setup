import tkinter as tk
from pandas import DataFrame, plotting
import time
import screeninfo
from tkinter import Tk, RIGHT, BOTH, LEFT, BOTTOM, NW, TOP, N, W, E, S, Y
from tkinter.ttk import Frame, Button, Style, Label
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime
import random as rdm
from threading import Timer

MENU_BACKGROUND_COLOR = (228, 55, 36)
MENUBAR_BACKGROUND_COLOR = (170, 65, 50)
ACTIVE_COLOR = tuple(map(sum, zip(MENU_BACKGROUND_COLOR, (+10, +10, +10))))


def _from_rgb(rgb):
    """translates an rgb tuple of int to a tkinter friendly color code
    """
    return "#%02x%02x%02x" % rgb


class Statistics:
    def __init__(self, trial_types, previous_performance, trial_number=None, trial_plot_span=15,
                 trial_labels=('Blocked', 'Smell', 'Visual', 'Opened')):

        assert isinstance(trial_types, tuple), \
            'Trial types must be a tuple of the states throughout the experiment.'
        assert (isinstance(previous_performance, dict) and
                all(isinstance(key, datetime.datetime) and 0<=val<=100 for key, val in previous_performance.items())) \
            or isinstance(previous_performance, type(None)), \
            'Previous performance must be a dict with date-number (int or float between 0 and 100) throughout.'
        if trial_number:
            assert isinstance(trial_number, int) and 0 < trial_number <= len(trial_types), \
                'Trial number must be an corresponding to the length of trial types or a lower value, greater than 0.'
        assert isinstance(trial_plot_span, int) and 0 < trial_number <= 101, \
            'Trial span must be an integer corresponding to the number of trials visible in the trial_plot.'

        self.trial_types = trial_types
        self.previous_performance = previous_performance
        self.trial_number = trial_number if trial_number else len(self.trial_types)
        self.trial_plot_span = trial_plot_span
        self.trial_plot_labels = trial_labels

        self.current_trial = 0
        self.current_trial_marker = None

        plt.Figure(figsize=(20, 20), dpi=100)
        self.position_axis = plt.subplot2grid((2, 2), (0, 0), colspan=2)
        self.speed_axis = self.position_axis.twinx()

        plotting.register_matplotlib_converters()

        self.trace_data = {
                'Timestamp': [],
                'Position': [],
                'Speed': []
            }

        self.position_plot, = self.position_axis.plot([], [], label='Position', color='black')
        self.speed_plot, = self.speed_axis.plot([], [], label='Speed', color='blue')

        self.trial_axis = plt.subplot2grid((2, 2), (1, 0))
        x = range(1, len(self.trial_types) + 1)
        self.trial_axis.set_xticks(x)
        trial_points = [list(t) for t in zip(x, self.trial_types)]
        self.trial_markers = [self.trial_axis.plot(*p, marker='o', color='blue', zorder=4, markersize=12.5,
                                                   fillstyle='none')[0]
                              for p in trial_points]
        self.colored_markers = (('blue', 'o'),
                                ('blue', '<'),
                                ('green', 'o'),
                                ('green', '<'),
                                ('red', 'o'),
                                ('red', '<'))

        self.performance_axis = plt.subplot2grid((2, 2), (1, 1))
        self.success_rate = 0
        self.current_performance, = self.performance_axis.bar(datetime.datetime.today(), 0, color='#8c564b')
        height = self.current_performance.get_height()
        self.current_performance_text = self.performance_axis.text(
            self.current_performance.get_x() + self.current_performance.get_width() / 2., 1.025 * height,
            '%d' % int(height), ha='center', va='bottom')
        self.current_performance_text.set_clip_on(True)

        plt.tight_layout()

        self.position_axis.set_title('Speed and Position Trace over Time')
        self.position_axis.set_xlabel('Time since Trial Start [s]')
        self.position_axis.set_ylabel('Position Voltage [V]')
        self.position_axis.set_ylim(-0.15 + (-.102 * 5), 5)
        self.position_axis.legend(handles=[self.position_plot, self.speed_plot], loc='upper left')

        # Patches
        self.trial_patch = self.position_axis.add_patch(matplotlib.patches.Rectangle((0, -0.25), 0, 0.25,
                                                                                     color='red', visible=True,
                                                                                     label='Trial Phase'))
        self.reward_patch = self.position_axis.add_patch(matplotlib.patches.Rectangle((0, -0.25), 0, 0.25,
                                                                                      color='green', visible=True,
                                                                                      label='Reward Phase'))
        self.inter_trial_patch = self.position_axis.add_patch(matplotlib.patches.Rectangle((0, -0.25), 0, 0.25,
                                                                                           color='blue', visible=True,
                                                                                           label='Inter-Trial Phase'))
        self.speed_axis.legend(handles=[self.trial_patch, self.reward_patch, self.inter_trial_patch],
                               bbox_to_anchor=(0., 0., 1., .102), loc='lower left', ncol=3, mode="expand",
                               borderaxespad=0.)
        self.current_phase = self.trial_patch

        self.speed_axis.set_ylim(-0.15 + (-.102 * 5), 5)
        self.speed_axis.set_ylabel('Speed Voltage [V]')

        self.trial_axis.set_title('Trial Types')
        self.trial_axis.set_xlabel('Current Trial')
        self.trial_axis.set_yticks((0, 1, 2, 3))
        self.trial_axis.set_yticklabels(self.trial_plot_labels, rotation=45)
        self.current_trial_marker = self.trial_axis.axvline(self.current_trial, color='cyan',
                                                            linewidth=12.5, zorder=1)
        self.trial_axis.axvline(self.trial_number + 0.5, color='black', linewidth=6.6, zorder=2)
        finish_line = self.trial_axis.axvline(self.trial_number + 0.5, color='white',
                                              linestyle='--', linewidth=5, zorder=3)
        finish_line.set_dashes([2, 2])  # 2pt line, 2pt break, 10pt line, 2pt break
        finish_label = self.trial_axis.text(self.trial_number + 0.7, 1, 'Finish Line', rotation=-90, fontsize=12)
        finish_label.set_clip_on(True)
        self.trial_axis.set_xlim(0.5, self.trial_plot_span + 0.5)

        self.performance_axis.set_title('Performance over Time')
        self.performance_axis.set_xlabel('Training on Date')

        data_points = tuple(zip(*self.previous_performance.items()))
        bars = self.performance_axis.bar(data_points[0], data_points[1], color='#1f77b4')
        for bar in bars:
            height = bar.get_height()
            text = self.performance_axis.text(bar.get_x() + bar.get_width() / 2., 1.025 * height, round(height, 1),
                                              ha='center', va='bottom')
            text.set_clip_on(True)

        days = matplotlib.dates.DayLocator()
        days_fmt = matplotlib.dates.DateFormatter('%d.%m')
        self.performance_axis.xaxis.set_major_locator(days)
        self.performance_axis.xaxis.set_major_formatter(days_fmt)
        self.performance_axis.set_xticks(tuple((*self.previous_performance.keys(), datetime.datetime.today())))
        self.performance_axis.set_xlim(datetime.datetime.today() - datetime.timedelta(days=8),
                                       datetime.datetime.today() + datetime.timedelta(days=1))
        self.performance_axis.set_ylabel('Percent Success [%]')
        self.performance_axis.set_ylim((0, 110))
        self.performance_axis.set_yticks((0, 25, 50, 75, 100))
        self.performance_axis.axhline(80, color='black', label='Learned')
        self.performance_axis.text(datetime.datetime.today() + datetime.timedelta(days=1), 82.5,
                                   'Learned', horizontalalignment='right')

        self.statistics_figure = plt.gcf()
        self.statistics_figure.set_size_inches(w=11, h=7)
        self.statistics_figure.set_facecolor(tuple(c / 255 for c in MENU_BACKGROUND_COLOR))

        self.pause_thread = None
        bbox = dict(boxstyle='square', lw=3, ec='red',
                    fc=(0.9, 0.9, .9, .5))
        self.pause_text = self.statistics_figure.text(0.5, 0.5, 'Paused.',
                                                      ha='center', va='center', fontsize=80,
                                                      color='red', bbox=bbox)
        self.pause_text.set_visible(False)

    def update_traces(self, new_data, blit=True):
        # adapted from https://stackoverflow.com/questions/40126176/fast-live-plotting-in-matplotlib-pyplot
        self.trace_data = new_data

        if blit:
            # cache the background
            position_background = self.statistics_figure.canvas.copy_from_bbox(self.position_axis.bbox)

        self.position_plot.set_data(self.trace_data['Timestamp'], self.trace_data['Position'])
        self.speed_plot.set_data(self.trace_data['Timestamp'], self.trace_data['Speed'])
        self.current_phase.set_width(self.trace_data['Timestamp'][-1] - self.current_phase.get_x())

        if blit:
            # restore background
            self.statistics_figure.canvas.restore_region(position_background)

            # redraw just the points
            try:
                self.position_axis.draw_artist(self.position_plot)
                self.speed_axis.draw_artist(self.speed_plot)
                self.position_axis.draw_artist(self.current_phase)

            except ValueError:
                print('During trace-plotting a ValueError has occured!')

            # fill in the axes rectangle
            self.statistics_figure.canvas.blit(self.position_axis.bbox)

        else:
            # redraw everything
            self.statistics_figure.canvas.draw()

    def update_phase(self, new_phase):
        end_last_phase = self.current_phase.get_x() + self.current_phase.get_width()
        if new_phase == 'Trial':
            self.trial_patch.set_visible(True)
            self.current_phase = self.trial_patch
        elif new_phase == 'Reward':
            self.reward_patch.set_visible(True)
            self.current_phase = self.reward_patch
        elif new_phase == 'Inter-Trial':
            self.inter_trial_patch.set_visible(True)
            self.current_phase = self.inter_trial_patch
        else:
            raise ValueError(f'Unknown command received: {new_phase}')
        self.current_phase.set_x(end_last_phase)

    def pause_function(self, frequency, counter=0):
        counter = counter % 2
        if counter == 1:
            color = 'black'
        else:
            color = 'yellow'

        counter += 1

        bbox = dict(boxstyle='square', lw=3, ec=color,
                    fc=(0.9, 0.9, .9, .5))
        self.pause_text.set_bbox(bbox)

        self.pause_text.set_color(color)

        self.pause_thread = Timer(1. / frequency, self.pause_function, args=(frequency, counter,))
        self.pause_thread.daemon = True
        self.pause_thread.start()

    def show_blinking_pause(self):
        self.pause_text.set_visible(True)
        self.pause_function(2)

    def end_blinking_pause(self):
        if self.pause_thread:
            self.pause_thread.cancel()
        self.pause_text.set_visible(False)

    def new_trial(self, duration, result_code):
        print("new trial!")
        self.trace_data = {
                'Timestamp': [],
                'Position': [],
                'Speed': []
            }

        self.position_plot.set_data([], [])
        self.speed_plot.set_data([], [])
        self.position_axis.set_xlim(0, duration)

        # Reset Patches
        self.trial_patch.set_width(0)
        self.trial_patch.set_visible(True)
        self.reward_patch.set_width(0)
        self.reward_patch.set_visible(False)
        self.inter_trial_patch.set_width(0)
        self.inter_trial_patch.set_visible(False)
        self.current_phase = self.trial_patch

        if self.current_trial > 0:
            self.trial_markers[self.current_trial - 1].set_fillstyle('full')
            self.trial_markers[self.current_trial - 1].set_color(self.colored_markers[result_code][0])
            self.trial_markers[self.current_trial - 1].set_marker(self.colored_markers[result_code][1])
            if result_code > 1:
                self.success_rate = (self.success_rate * (self.current_trial - 1) + 1) / self.current_trial
                self.current_performance.set_height(self.success_rate * 100)
                self.current_performance_text.set_y(1.025 * self.success_rate * 100)
                self.current_performance_text.set_text(str(round(self.success_rate * 100, 1)))
            else:
                self.success_rate = (self.success_rate * (self.current_trial - 1)) / self.current_trial
                self.current_performance.set_height(self.success_rate * 100)
                self.current_performance_text.set_y(1.025 * self.success_rate * 100)
                self.current_performance_text.set_text(str(round(self.success_rate * 100, 1)))

        self.current_trial += 1
        self.current_trial_marker.set_xdata(self.current_trial)
        plot_border = (self.trial_plot_span - 1) / 2 + 0.5
        self.trial_axis.set_xlim(max(0.5, self.current_trial - plot_border),
                                 max(0.5 + self.trial_plot_span, self.current_trial + plot_border))


class StatisticsFrame(Frame):
    def __init__(self, screen, root, statistics, text1, text2, trial_number, disk_states, go_event, stop_event,
                 trial_labels=('Blocked', 'Smell', 'Visual', 'Opened'), show_fps=False, *args, **kwargs):
        Frame.__init__(self, root, *args, **kwargs)
        self.screen = screen
        self.root = root
        self.statistics = statistics

        self.pack(fill=BOTH, expand=True)
        self.style = Style()
        self.style.theme_use("default")

        self._message_text = tk.StringVar()
        self.canvas = None
        self.pause = False
        self.pause_button_text = tk.StringVar()
        self.start_time = time.time()
        self.current_trial = -1
        self.trial_number = trial_number
        self.disk_states = disk_states
        self.trial_labels = trial_labels
        self.trial_info_text = tk.StringVar()
        self.experiment_info_text = tk.StringVar()
        self.success_rate_string = '0'
        self.fps_text = tk.StringVar()
        self.init_ui(text1, text2, show_fps)
        self.go_event = go_event
        self.stop_event = stop_event

    def pause_experiment(self, *args):
        self.pause = not self.pause
        if self.pause:
            self.pause_button_text.set("▶ Pause Experiment")
            self.show_message()
            self.go_event.clear()
        else:
            self.pause_button_text.set("⏸ Pause Experiment")
            self._message_text.set('')
            self.go_event.set()

    def stop_experiment(self, *args):
        self.stop_event.set()
        self.go_event.set()

    def remove_message(self, *args):
        self._message_text.set('')

    def show_message(self, *args):
        self._message_text.set('Experiment will pause after current trial.')
        tk.Widget.after(self, 3000, self.remove_message)

    def update_time(self):
        passed_time = str(datetime.timedelta(seconds=round(time.time() - self.start_time, 2))).split(".")[0]
        self.experiment_info_text.set('Experiment info:\n' +
                                      f'Performance: {self.success_rate_string}%\n' +
                                      f'Elapsed time: {passed_time}')
        self.after(1000, self.update_time)

    def update_phase(self, new_phase):
        self.statistics.update_phase(new_phase)

    def update_fps(self, new_fps):
        self.fps_text.set(f'Current FPS: {new_fps}')

    def update_trial(self, duration):
        self.current_trial += 1
        self.trial_info_text.set('Trial info:\n' +
                                 f'Current trial: {self.current_trial}/{self.trial_number}\n' +
                                 f'Disk state: {self.trial_labels[self.disk_states[self.current_trial]]}')
        passed_time = str(datetime.timedelta(seconds=round(time.time() - self.start_time, 2))).split(".")[0]

        self.success_rate_string = str(round(self.statistics.success_rate * 100, 1))
        self.experiment_info_text.set('Experiment info:\n' +
                                      f'Performance: {self.success_rate_string}%\n' +
                                      f'Elapsed time: {passed_time}')
        self.statistics.end_blinking_pause()
        self.statistics.new_trial(duration, rdm.randint(0, 4))

    def init_ui(self, text1, text2, show_fps):
        Style().configure('TFrame', background=_from_rgb(MENU_BACKGROUND_COLOR))
        Style().configure('TButton', font=("Helvetica", 30))
        Style().configure('TLabel', font=("Helvetica", 25), background=_from_rgb(MENU_BACKGROUND_COLOR), spacing3=100)
        Style().configure('Message.TLabel', font=("Helvetica", 20), background=_from_rgb(MENU_BACKGROUND_COLOR))
        Style().map('TButton', background=[('active', _from_rgb(ACTIVE_COLOR)),
                                           ("!disabled", _from_rgb(MENU_BACKGROUND_COLOR))])

        canvas = tk.Canvas(self, bd=0, highlightthickness=0, relief='ridge')
        canvas.configure(background=_from_rgb(MENU_BACKGROUND_COLOR))
        canvas.grid(row=0, column=0, sticky=W+E)
        title_text = canvas.create_text(10, 5, anchor=NW, font="Arial 30 bold",
                                        text="Experiment Statistics")

        information_outer_frame = Frame(self, borderwidth=1)
        information_outer_frame.grid(row=1, column=0, sticky=N+W+E+S)

        figure_frame = Frame(information_outer_frame, borderwidth=0)
        figure_frame.pack(fill=BOTH, side=LEFT, expand=True)

        text_frame = Frame(information_outer_frame, borderwidth=0)
        text_frame.pack(fill=BOTH, side=RIGHT, expand=True, padx=(30, 30))
        text_frame.grid_propagate(False)

        figure = FigureCanvasTkAgg(self.statistics.statistics_figure, figure_frame)
        figure.get_tk_widget().pack(fill=BOTH, expand=True)

        Label(text_frame, text=text1).grid(row=0, column=0, sticky=N+W+E+S)

        Label(text_frame, text=text2).grid(row=1, column=0, sticky=N+W+E+S)

        Label(text_frame, textvariable=self.trial_info_text).grid(row=2, column=0, sticky=N+W+E+S)
        passed_time = str(datetime.timedelta(seconds=round(time.time() - self.start_time, 2))).split(".")[0]
        self.trial_info_text.set('Trial info:\n' +
                                 f'Current trial: -1/{self.trial_number}\n' +
                                 f'Disk state: Blocked')

        Label(text_frame, textvariable=self.experiment_info_text).grid(row=3, column=0, sticky=N+W+E+S, pady=(0, 40))
        self.experiment_info_text.set('Experiment info:\n' +
                                      f'Performance: 100\n' +
                                      f'Elapsed time: {passed_time}')

        for row in range(4):
            text_frame.grid_rowconfigure(row, weight=1)

        button_frame_outer = Frame(self, borderwidth=1)
        button_frame_outer.grid(row=2, column=0, sticky=W+E)

        Label(button_frame_outer, textvariable=self._message_text, style='Message.TLabel').place(x=10, rely=0.5,
                                                                                                 anchor=W)
        self._message_text.set('')

        fps_label = Label(button_frame_outer, textvariable=self.fps_text, style='Message.TLabel')
        fps_label.place(relx=0.785, rely=0.5, anchor=W)
        self.fps_text.set('')

        if not show_fps:
            fps_label.place_forget()

        button_frame_inner = Frame(button_frame_outer, borderwidth=1)
        button_frame_inner.pack(side=BOTTOM, fill=None, expand=False)
        end_button = Button(button_frame_inner, text="⏹ End Experiment", command=self.stop_experiment)
        end_button.pack(side=RIGHT, padx=20, pady=20)
        pause_button = Button(button_frame_inner, textvariable=self.pause_button_text, command=self.pause_experiment)
        self.pause_button_text.set("⏸ Pause Experiment")
        pause_button.pack(side=LEFT, padx=20, pady=20)

        self.grid_rowconfigure(1, weight=1)

        text_bounds = canvas.bbox(title_text)
        canvas.config(width=self.screen.width, height=text_bounds[3]+5)
        self.update()
        width = canvas.winfo_width()

        points = [(0, 0),
                  (width, 0),
                  (width, text_bounds[3] * 0.6),
                  (text_bounds[2] + 30, text_bounds[3] * 0.6),
                  (text_bounds[2] + 10, text_bounds[3] + 5),
                  (0, text_bounds[3] + 5)]

        background = canvas.create_polygon(points, outline='#f11', fill=_from_rgb(MENUBAR_BACKGROUND_COLOR), width=2)
        canvas.tag_lower(background)
        self.update_time()


def tracer_func(instructions, go_event, stop_event, instruction_pipe, latest_line, screen):
    # Initialization
    records = {
        'Timestamp': [],
        'Position': [],
        'Speed': []
    }

    new_data = None
    paused = False

    window = Tk()
    window.overrideredirect(True)
    window.title("Statistics Window")
    if screen.x > 0:
        x_string = f'+{screen.x}'
    else:
        x_string = str(screen.x)
    geometry_string = f'{screen.width}x{screen.height}{x_string}+0'
    print(geometry_string)
    window.geometry(geometry_string)

    window.state('normal')

    trial_number = 100
    disk_random = 1 * [0] + 1 * [1] + 1 * [2] + 1 * [3]
    disk_states = tuple(disk_random[int(len(disk_random) * rdm.random())] for _ in range(trial_number))
    performance = {
        datetime.datetime.today() - datetime.timedelta(days=1): 90.752,
        datetime.datetime.today() - datetime.timedelta(days=7): 80.333333,
        datetime.datetime.today() - datetime.timedelta(days=14): 20,
        datetime.datetime.today() - datetime.timedelta(days=20): 0
    }

    statistics_collection = Statistics(disk_states, performance, trial_number=15, trial_plot_span=11)

    mouse_info = 'Current Mouse: \nName: Mickey \nWeight: Fat \nBirthdate: 01.01.1940 \nMLA-NR: WD-40'

    rat_info = 'Current Rat: \nName: Steve \nWeight: Fatter \nBirthdate: 01.01.1945 \nMLA-NR: MLA-007'

    statistics_frame = StatisticsFrame(screen, window, statistics_collection, mouse_info, rat_info, 15, disk_states,
                                       go_event, stop_event, show_fps=True)
    window.update()

    def update_data(current_line, shared_array, target_fps=300):
        start = time.perf_counter()
        if current_line != list(shared_array):
            current_line = list(shared_array)
            records['Timestamp'].append(current_line[0])
            records['Position'].append(current_line[1])
            records['Speed'].append(current_line[2])
        target = 1. / target_fps
        passed = time.perf_counter() - start
        differ = target - passed
        t = Timer(differ, update_data, args=(current_line, shared_array, target_fps, ))
        t.daemon = True
        t.start()

    update_data(new_data, latest_line)

    start_time = time.perf_counter()
    x = 0.5
    counter = 0

    while True:
        # Check for new instructions
        if instruction_pipe.poll():
            command = instruction_pipe.recv()
            if command is instructions.Pause:
                paused = True
                statistics_frame.statistics.show_blinking_pause()
            elif command is instructions.Ready:
                paused = False
                records = {
                    'Timestamp': [],
                    'Position': [],
                    'Speed': []
                }
                go_event.set()
            elif command is instructions.Reset:
                duration = instruction_pipe.recv()
                statistics_frame.update_trial(duration)
                paused = True
            elif command is instructions.Dump:
                df = DataFrame(records)
                df.to_csv('TRACER.csv')
            elif command is instructions.Phase:
                new_phase = instruction_pipe.recv()
                statistics_frame.update_phase(new_phase)
            elif command is instructions.Stop:
                break
            else:
                raise ValueError(f'Unknown command received: {command}')

        statistics_frame.root.update()

        if paused:
            statistics_frame.statistics.statistics_figure.canvas.draw()
            time.sleep(50 / 1000)
            continue

        if records['Timestamp']:
            statistics_frame.statistics.update_traces(records)

        counter += 1
        if (time.perf_counter() - start_time) > x:
            statistics_frame.update_fps(int(counter / (time.perf_counter() - start_time)))
            print("FPS: ", counter / (time.perf_counter() - start_time))
            counter = 0
            start_time = time.perf_counter()

    print(len(records['Timestamp']))
    print('TRACER STOPPED.')


def main():
    screens = screeninfo.get_monitors()
    for screen in screens:
        print(screen)

    window = Tk()
    window.overrideredirect(True)
    window.title("Statistics Window")
    screen_left = False
    if screen_left:
        movement = '+'
    else:
        movement = '-'
    geometry_string = f'100x100{movement}{screens[1].width}+0'
    window.geometry(geometry_string)
    window.state('zoomed')

    trial_number = 100
    disk_random = 1 * [0] + 1 * [1] + 1 * [2] + 1 * [3]
    disk_states = tuple(disk_random[int(len(disk_random) * rdm.random())] for _ in range(trial_number))
    performance = {
        datetime.datetime.today() - datetime.timedelta(days=1): 90.752,
        datetime.datetime.today() - datetime.timedelta(days=7): 80.333333,
        datetime.datetime.today() - datetime.timedelta(days=14): 20,
        datetime.datetime.today() - datetime.timedelta(days=20): 0
    }

    statistics_collection = Statistics(disk_states, performance, trial_number=15, trial_plot_span=11)

    mouse_info = 'Current Mouse: \nName: Mickey \nWeight: Fat \nBirthdate: 01.01.1940 \nMLA-NR: WD-40'

    rat_info = 'Current Rat: \nName: Steve \nWeight: Fatter \nBirthdate: 01.01.1945 \nMLA-NR: MLA-007'

    StatisticsFrame(window, statistics_collection, mouse_info, rat_info, trial_number=15, disk_states=disk_states)
    window.update()

    def outside_mainloop():
        print("running")
        window.after(1000, outside_mainloop)

    try:
        window.after(1000, outside_mainloop)
        window.mainloop()

    finally:
        print("stopped running")


if __name__ == '__main__':
    main()
