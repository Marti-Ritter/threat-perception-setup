import sys
import tkinter as tk
import matplotlib.pyplot as plt
import matplotlib as mpl
import numpy as np

import sys
import tkinter as tk
from multiprocessing import Process, Event

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from src.MyApp import (
    SettingsWindow, PlotWindow, MyConsole, MyStatusFrame, MyCamFrame, MySubjectWindow, MyStatusBar, MyStatusReporter,
    SubjectsSelection)

from src.MySubject import MySubjectManager, MySubjectType

trial_settings = {
    "repeats": {"value": 5, "type": "int", "randomizable": False, "label": "Number of trials"},
    "start_delay": {"value": 0, "type": "float", "randomizable": False, "label": "Start Delay"},
    "reward_delay": {"value": 1, "type": "float", "randomizable": False, "label": "Reward Delay"},
    "trial_timeout": {"value": 1, "type": "float", "randomizable": False, "label": "Trial Timeout"},
    "lick_timeout": {"value": 1, "type": "float", "randomizable": False, "label": "Lick Timeout"},
    "timeout_punish": {"value": 1, "type": "float", "randomizable": False, "label": "Timeout Punish"},
    "fail_punish": {"value": 1, "type": "float", "randomizable": False, "label": "Fail Punish Time"},
    "reward_time": {"value": 1, "type": "float", "randomizable": False, "label": "Reward Tim"},
}

bpod_settings = {

    "serial_port": {"value": "/dev/ttyACM0", "type": "file", "filetypes": [("Serial", "*ttyACM*")],
                    "label": "Bpod Serial Port"},
    "session_name": {"value": "session", "randomizable": False, "type": "str", "label": "Session Name"},

}

pi_settings = {

    "serial_port": {"value": "/dev/ttyACM0", "type": "file", "filetypes": [("Serial", "*ttyACM*")],
                    "label": "Bpod Serial Port"},
    "session_name": {"value": "session", "randomizable": False, "type": "str", "label": "Session Name"},

}


class Application(tk.Frame):

    def __init__(self, master=None):
        super().__init__(master)

        from tkinter import font
        f = font.nametofont(font.names()[7])

        self.bpod_process = None

        self.flags = {
            "pod_ready": Event(),
            "pi_ready": Event(),
            "run": Event()
        }


        self.status = MyStatusReporter()


        self.subject_managers = [
            MySubjectManager(MySubjectType.MOUSE, "mice"),
            MySubjectManager(MySubjectType.RAT,"rats")
        ]
        for m in self.subject_managers:
            m.load_subjects()

        self.trial_settings_template = trial_settings
        self.bpod_settings_template = bpod_settings
        self.pi_settings_template = pi_settings

        self.left_frame = tk.Frame(self.master)
        self.left_frame.grid(row=0, column=0)

        self.right_frame = tk.Frame(self.master, bd=2, relief="solid")
        self.right_frame.grid(row=0, column=1)

        self.subject_selection = SubjectsSelection(self.left_frame, self.subject_managers)
        self.subject_selection.grid(row=0, column=0, sticky="wsns")

        self.settings_frame = tk.Frame(self.left_frame)
        self.settings_frame.grid(row=0, column=1,sticky = "ws")

        self.trial_controls = tk.Frame(self.left_frame)
        self.trial_controls.grid(row=1, column=1)

        self.status_frame = tk.Frame(self.left_frame, bd=1, relief="solid")
        self.status_frame.grid(row=2, column=0)

        tk.Label(self.settings_frame, text="Experiment Settings", font=(f, 12, "bold")).grid(row=0, column=1)
        tk.Label(self.settings_frame, text="Bpod Settings", font=(f, 12, "bold")).grid(row=0, column=2)
        tk.Label(self.settings_frame, text="Raspberrypi Settings", font=(f, 12, "bold")).grid(row=0, column=3)

        self.trial_settings_frame = tk.Frame(self.settings_frame, bd=2, relief="solid")
        self.trial_settings_frame.grid(row=1, column=1, sticky="NS")

        self.bpod_settings_frame = tk.Frame(self.settings_frame, bd=2, relief="solid")
        self.bpod_settings_frame.grid(row=1, column=2, sticky="NS")

        self.pi_settings_frame = tk.Frame(self.settings_frame, bd=2, relief="solid")
        self.pi_settings_frame.grid(row=1, column=3, sticky="NS")

        self.camframe_1 = MyCamFrame(self.settings_frame)
        self.camframe_1.grid(row=2, column=1, padx=5, pady=5)

        self.camframe_2 = MyCamFrame(self.settings_frame)
        self.camframe_2.grid(row=2, column=2, padx=5, pady=5)

        self.camframe_3 = MyCamFrame(self.settings_frame)
        self.camframe_3.grid(row=2, column=3, padx=5, pady=5)

        self.bpod_control_frame = tk.Frame(self.right_frame)
        self.bpod_control_frame.grid(row=0, column=0, sticky="NS")

        self.pi_control_frame = tk.Frame(self.right_frame)
        self.pi_control_frame.grid(row=1, column=0, sticky="NS")

        self.experiment_control_frame = tk.Frame(self.right_frame)
        self.experiment_control_frame.grid(row=2, column=0)

        self.create_main_window()

        self.i = 0
        self.dummy_print()

    def create_subject_window(self):

        def callback():
            self.subject_selection.update_entries()

        self.subject_window = MySubjectWindow(self.settings_frame,self.subject_managers, callback = callback)

    def create_plot_window(self):

        fig, ax = self.create_figure()
        self.fig = fig
        self.ax = ax

        def callback():
            del self.plot_window

        self.plot_window = PlotWindow(self.master, callback, fig, ax)

        self.camframe_1 = MyCamFrame(self.plot_window.right_frame)
        self.camframe_1.grid(row=0, column=0, padx=5, pady=5)

        self.camframe_2 = MyCamFrame(self.plot_window.right_frame)
        self.camframe_2.grid(row=1, column=0, padx=5, pady=5)

        self.camframe_3 = MyCamFrame(self.plot_window.right_frame)
        self.camframe_3.grid(row=2, column=0, padx=5, pady=5)


        self.make_trial_controls(self.plot_window.bottom_frame)
        MyStatusBar(self.plot_window.status_frame, self.status).pack()

    def create_figure(self):

        fig = plt.figure(constrained_layout=True, figsize=(10, 5))

        widths = [10, 1]
        heights = [2, 1, 2]

        spec2 = mpl.gridspec.GridSpec(ncols=2, nrows=3, figure=fig, width_ratios=widths,
                                      height_ratios=heights)

        ax1 = fig.add_subplot(spec2[0, 0])
        ax2 = fig.add_subplot(spec2[:, 1])
        ax3 = fig.add_subplot(spec2[1, 0])
        ax4 = fig.add_subplot(spec2[2, 0])

        ax = {"session": ax1, "legend": ax2, "trace": ax3, "hist": ax4}
        return fig, ax

    def plot(self):
        from src.SessionPlotter import TPMSessionLoad, TPMSessionPlotter

        if not hasattr(self, "plot_window"):
            self.create_plot_window()

        loader = TPMSessionLoad()
        loader.path = "./sessions/dummy_session.csv"
        loader.trial_indices = list(np.zeros(100, dtype=int))
        loader.trial_versions = [{"name": "standard"}]
        loader.load_session(loader.path)

        plotter = TPMSessionPlotter(loader)
        plotter.settings = {
            "ymin": 0,
            "ymax": 1,
            "hist_bins": 10,
            "margin": 0.2,
            "state_bar_height": 0.05,
            "success_color": (0, 1, 0),
            "desaturation": 0.7,
            "fail_color": (1, 0, 0),
            "plot_window": 20,
            "workspace_path": "./experiments/",
            "figure_path": "./plot.pdf", "type": "df .png .jpg . svg",
        }

        loader.settings = plotter.settings
        plotter.plot_experiment(self.ax)
        plotter.plot_trace(self.ax["trace"])
        self.plot_window.draw()

    def create_main_window(self):
        self.make_trial_settings()
        self.make_bpod_settings()
        self.make_pi_settings()
        MyStatusBar(self.status_frame, self.status).grid()


        self.make_trial_controls(self.trial_controls)

        self.make_flag_widgets()

    def make_flag_widgets(self):

        running = MyStatusFrame(self.experiment_control_frame, name="Running")
        running.grid()

        self.flag_widgets = {
            "run": running
        }

        self.make_pi_controls()
        self.make_bpod_controls()

    def make_trial_controls(self, root):

        padx = 10
        pady = 5

        self.start_screens_button = tk.Button(root, text="Start Screens", command=self.start_screen)
        self.start_screens_button.grid(row=0, column=0, padx=padx, pady=pady)

        self.stop_screens_buttion = tk.Button(root, text="Stop Screens", command=self.stop_screen)
        self.stop_screens_buttion.grid(row=0, column=1, padx=padx, pady=pady)

        # self.initialize_button = tk.Button(root, text="Initialize", command=self.initialize)
        # self.initialize_button.grid(row=0, column=2, padx=padx, pady=pady)

        self.start_button = tk.Button(root, text="Start Experiment", command=self.start_exp)
        self.start_button.grid(row=0, column=3, padx=padx, pady=pady)

        # self.pause_button = tk.Button(root, text="Pause Experiment", command=self.pause_exp)
        # self.pause_button.grid(row=0, column=4, padx=padx, pady=pady)

        tk.Button(root, text="Subject Manager", command=self.create_subject_window).grid(row=0, column=4, padx=padx, pady=pady)


        self.quit_button = tk.Button(root, text="Stop Experiment", command=self.quit_exp)
        self.quit_button.grid(row=0, column=5, padx=padx, pady=pady)

    def make_pi_controls(self):

        padx = 10
        pady = 10

        status = MyStatusFrame(self.pi_control_frame,name = "PI Status")
        status.grid(row=0, column=0, padx=padx, pady=pady, sticky="NS")
        self.flag_widgets["pi_ready"] = status

        screen_status = MyStatusFrame(self.pi_control_frame, name="Screen Status")
        screen_status.grid(row=0, column=1, padx=padx, pady=pady, sticky="NS")
        self.flag_widgets["screen_ready"] = screen_status

        self.reset_pi_button = tk.Button(self.pi_control_frame, text="Reset connection", command=self.reset_pi)
        self.reset_pi_button.grid(row=1, column=0, padx=padx, pady=pady)

        self.pi_console = MyConsole(self.pi_control_frame)
        self.pi_console.grid(row = 2,columnspan = 2,sticky = "WE")

    def make_bpod_controls(self):

        padx = 10
        pady = 10

        status = MyStatusFrame(self.bpod_control_frame,"POD status")
        status.grid(row=0, column=0, padx=padx, pady=pady, sticky="NS")

        self.flag_widgets["pod_ready"] = status

        self.reset_pod_button = tk.Button(self.bpod_control_frame, text="Reset connection", command=self.quit_exp)
        self.reset_pod_button.grid(row=0, column=1, padx=padx, pady=pady)

        self.bpod_console = MyConsole(self.bpod_control_frame)
        self.bpod_console.grid(row=2, columnspan=2, sticky="WE")
    def dummy_print(self):
        self.i += 1

        self.bpod_console.println("counter: {c}".format(c=self.i))
        self.pi_console.println("counter: {c}".format(c=self.i))

        if self.i > 50:
            self.bpod_console.clear()
            self.pi_console.clear()
            self.i = 0

        self.after(100, self.dummy_print)

    def connect_pi(self, ip, port):

        from src.Communication import create_connection
        self.pi_connection = create_connection(ip, port)

    def start_screen(self):
        from src.Communication import start_screen

        if hasattr(self, "pi_connection"):
            start_screen(self.pi_connection)

    def stop_screen(self):
        from src.Communication import close_screen

        if hasattr(self, "pi_connection"):
            close_screen(self.pi_connection)

    def reset_pi(self):

        from src.Communication import shutdown, connection_settings

        if hasattr(self, "pi_connection"):
            shutdown(self.pi_connection, 0)

        self.connect_pi(connection_settings["raspi_ip"], connection_settings["port"])

    def lock_settings(self):

        self.trial_settings.lock()
        self.bpod_settings.lock()
        self.pi_settings.lock()

    def unlock_settings(self):

        self.trial_settings.unlock()
        self.bpod_settings.unlock()
        self.pi_settings.unlock()

    def make_trial_settings(self):

        def callback(export):
            pass

        self.trial_settings = SettingsWindow(self.trial_settings_frame, self.trial_settings_template, callback,
                                             window=False)

    def make_bpod_settings(self):

        def callback(export):
            pass

        self.bpod_settings = SettingsWindow(self.bpod_settings_frame, self.bpod_settings_template, callback,
                                            window=False)

    def make_pi_settings(self):

        def callback(export):
            pass

        self.pi_settings = SettingsWindow(self.pi_settings_frame, self.pi_settings_template, callback, window=False)


    def set_message(self, message):
        self.status["text"] = message

    def pi_ready_set(self):

        self.flags["pi_ready"].set()

    def pi_ready_clear(self):

        self.flags["pi_ready"].clear()

    def get_settings(self):

        assert hasattr(self, "trial_settings")
        assert hasattr(self, "bpod_settings")
        assert hasattr(self, "pi_settings")

        trial = self.trial_settings.settings.get_experiment_variables().get_settings_dict()
        bpod = self.bpod_settings.settings.get_experiment_variables().get_settings_dict()
        pi = self.pi_settings.settings.get_experiment_variables().get_settings_dict()

        return trial, bpod, pi

    def send_settings(self):

        trial, bpod, pi = self.get_settings()

    def initialize(self):
        from src.tpm_bpod_script import run_multiple_trials

        trial, bpod, pi = self.get_settings()

        self.flags["run"].clear()
        self.bpod_process = Process(target=run_multiple_trials, args=(trial, self.flags))
        self.bpod_process.start()

    def start_exp(self):

        self.lock_settings()
        self.plot()
        if self.bpod_process is None or not self.bpod_process.is_alive():
            self.initialize()

        self.flags["run"].set()

    def pause_exp(self):

        self.flags["run"].clear()

    def quit_exp(self):

        self.unlock_settings()
        if not self.bpod_process is None:
            self.bpod_process.terminate()

    def quit(self):

        self.quit_exp()
        self.master.destroy()
        self.master.quit()


root = tk.Tk()
app = Application(master=root)
root.protocol("WM_DELETE_WINDOW", root.quit)
app.mainloop()
sys.exit(0)
