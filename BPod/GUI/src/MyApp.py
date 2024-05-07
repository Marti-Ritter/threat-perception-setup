import enum
import tkinter as tk
from tkinter import ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .MyVariables import MySettingGroup, MySetting, MyTrialSettings

class SubjectsSelection(tk.Frame):

    def __init__(self, root, subject_managers, **kwargs):
        super(SubjectsSelection, self).__init__(root,**kwargs)

        self.subject_managers = subject_managers

        for i,m in enumerate(self.subject_managers):
            SubjectSelection(self, m).grid(row = i, column = 0, padx  = 5, pady = 5,sticky = "WNSE")

    def update_entries(self):
        for child in self.children.values():
            if isinstance(child,SubjectSelection):
                child.update_entries()

class SubjectSelection(tk.Frame):

    def __init__(self, root, subject_manager, **kwargs):
        super(SubjectSelection, self).__init__(root, height = 50, width = 50, bd = "1",relief = "solid", **kwargs)
        self.subject_manager = subject_manager

        tk.Label(self, text = self.subject_manager.subject_type.value).grid(row = 0)

        self.combo = ttk.Combobox(self)

        self.combo.grid(row = 1)
        self.combo.bind("<<ComboboxSelected>>", self.update_data)

        self.data = SubjectDataFrame(self, state="readonly")
        self.data.grid(row = 2)

        self.update_entries()


    def update_entries(self):

        names = [s.get_display_name() for s in self.subject_manager.get_subjects()]
        self.combo["value"] = names
        self.combo.current(0)
        self.update_data()

    def update_data(self,*args):

        i = self.combo.current()
        if i < len(self.subject_manager.subjects):
            subject = self.subject_manager.subjects[i]
            self.data.show_data(subject)



class MyStatusReporter:

    def __init__(self):

        self.status = tk.StringVar()
        self.set_status("DUMMY STATUS")

    def set_status(self, status_text):
        self.status.set(status_text)



class MyStatusBar(tk.Frame):

    def __init__(self, root, status_reporter, **kwargs):
        super(MyStatusBar, self).__init__(root, **kwargs)

        self.reporter = status_reporter
        self.label = tk.Label(self, textvariable = self.reporter.status)
        self.label.pack()


class MyStatus(enum.Enum):
    READY = ("READY", "orange")
    BUSY = ("BUSY", "red")
    RUNNING = ("RUNNING", "green")
    STANDBY = ("STANDBY", "orange")


class MyCamFrame(tk.Frame):

    def __init__(self, master=None):
        super(MyCamFrame, self).__init__(master=master, height=100, width=100, bd=1, relief="solid")

        tk.Label(self, text="CAMERA DUMMY").grid(padx=50, pady=50, sticky="NSWE")


class MyStatusFrame(tk.Frame):

    def __init__(self, master=None, name="default"):
        self.name = name

        super().__init__(master)

        self.name_label = tk.Label(self, text=self.name + ":")
        self.name_label.grid(row=0, column=0)

        self.status_label = tk.Label(self)
        self.status_label.grid(row=1, column=0)
        self.flag = None

        self.set_status(MyStatus.STANDBY)

    def set_flag(self, flag):
        self.flag = flag

    def set_status(self, status):
        assert isinstance(status, MyStatus)

        self.status = status
        self.update_idletasks()

    def update_idletasks(self):
        self.after(500, self.update_idletasks)

        self.configure(bg=MyStatus.STANDBY.value[1])
        self.name_label.configure(bg=MyStatus.STANDBY.value[1])
        self.status_label.configure(bg=MyStatus.STANDBY.value[1], text=MyStatus.STANDBY.value[0])


class MyConsole(tk.Frame):

    def __init__(self, master):
        super(MyConsole, self).__init__(master=master)

        scroll = tk.Scrollbar(self)
        scroll.grid(row=0, column=1, sticky="NS")

        self.console = tk.Text(self, height=10, width=25)
        self.console.grid(row=0, column=0, sticky="WE")

        scroll.config(command=self.console.yview)
        self.console.config(yscrollcommand=scroll.set)

    def println(self, text):
        self.console.insert(tk.END, text + "\n")
        self.console.see(tk.END)

    def print(self):
        pass

    def clear(self):
        self.console.delete(1.0, tk.END)


class MyWindow:

    def __init__(self, root, window=True, callback=None):

        self.callback = callback

        if window:
            self.frame = tk.Toplevel(root)

            self.frame.protocol("WM_DELETE_WINDOW", self.close)

        else:
            self.frame = tk.Frame(root,)
            self.frame.grid()


    def close(self):

        self.frame.destroy()
        self.callback()


class SubjectManagerFrame(tk.Frame):

    def __init__(self, master, subject_manager, height = 250, **kwargs):

        super(SubjectManagerFrame, self).__init__(master=master, **kwargs)



        self.subject_manager = subject_manager
        self.list_box = tk.Listbox(self, height = height)
        self.list_box.grid(row=0, column=0, columnspan=2, stick="NS")

        scroll = tk.Scrollbar(self)
        scroll.grid(row=0, column=3, sticky="NS")

        scroll.config(command=self.list_box.yview)
        self.list_box.config(yscrollcommand=scroll.set)

        self.list_box.bind("<Double-Button-1>", self.update_data)
        self.list_box.bind("<Up>", self.update_data)
        self.list_box.bind("<Down>", self.update_data)

        self.list_box.bind("<Delete>", self.remove_current_subject)



        self.data_frame = SubjectDataFrame(self)
        self.data_frame.grid(row=0, column=4)

        self.update_list()
        self.list_box.select_set(tk.END)

        tk.Button(self, text="Save Subject", command=self.save_current_subject).grid(row=1, column=0)
        tk.Button(self, text="Remove Subject", command=self.remove_current_subject).grid(row=1, column=1)

    def save_current_subject(self, *args):

        from src.MySubject import MySubject

        i = self.list_box.curselection()

        if len(i) == 0 or i[0] >= len(self.subject_manager.subjects):
            subject_data = self.data_frame.get_data()

            assert self.subject_manager.id_exists(subject_data["id"]) == False

            subject = MySubject(subject_data["id"], subject_data["name"], self.subject_manager.subject_type)
            self.subject_manager.add_subject(subject)
            self.update_list()
        else:


            subject_data = self.data_frame.get_data()

            subject = self.subject_manager.subjects[i[0]]
            if not subject_data["id"] == subject.id:
                assert self.subject_manager.id_exists(subject_data["id"]) == False

            for k, v in subject_data.items():
                subject.__setattr__(k, v)
            self.update_list()

    def remove_current_subject(self,*args):

        i = self.list_box.curselection()
        if len(i) > 0 and i[0] < len(self.subject_manager.subjects):
            subject = self.subject_manager.get_subject(i[0])
            self.subject_manager.delete_subject(subject)
            self.update_list()

    def update_list(self):

        self.list_box.delete(0, tk.END)

        for subject in self.subject_manager.subjects:
            self.list_box.insert(tk.END, subject.get_display_name())
        self.list_box.insert(tk.END, "ADD Subject")

    def update_data(self, event):


        i = self.list_box.curselection()[0]

        if event.keysym == "Down":
            i += 1

        elif event.keysym == "Up":
            i -= 1


        if i >= len(self.subject_manager.subjects):
            self.data_frame.show_empty()
        else:
            self.data_frame.show_data(self.subject_manager.subjects[i])


class SubjectDataFrame(tk.Frame):

    def __init__(self, master, state = "normal", **kwargs):

        super(SubjectDataFrame, self).__init__(master=master, **kwargs)

        self.id = tk.StringVar()
        self.name = tk.StringVar()

        tk.Label(self, text="Subject ID").grid(row=0, column=0)
        self.id_entry = tk.Entry(self, state = state,textvariable = self.id)
        self.id_entry.grid(row=0, column=1)

        tk.Label(self, text="Subject Nickname").grid(row=1, column=0)
        self.name_entry = tk.Entry(self, state = state,textvariable = self.name)
        self.name_entry.grid(row=1, column=1)

    def show_empty(self):
        self.id.set("")
        self.name.set("")

        # self.id_entry.delete(0, tk.END)
        # self.name_entry.delete(0, tk.END)

    def show_data(self, subject):
        self.show_empty()

        self.id.set(str(subject.id))
        self.name.set(subject.name)

    def get_data(self):
        return {
            "id": self.id.get(),
            "name": self.name.get()
        }


class MySubjectWindow(MyWindow):

    def __init__(self, root, subject_manager_list, **kwargs):
        super().__init__(root, **kwargs)

        self.manager_frames = []
        for i, m in enumerate(subject_manager_list):
            frame = SubjectManagerFrame(self.frame, m, bd=1, relief="solid", height = 20)
            frame.grid(row=0, column=i, pady=10, padx=10, sticky = "NS")
            self.manager_frames.append(
                frame
            )

    def close(self):

        for m in self.manager_frames:
            m.subject_manager.save_subjects()

        super(MySubjectWindow, self).close()


class PlotWindow(MyWindow):

    def __init__(self, root, callback, fig, ax, window=True, **kwargs):
        super(PlotWindow, self).__init__(root, **kwargs)

        self.fig = fig
        self.ax = ax

        self.right_frame = tk.Frame(self.frame)
        self.right_frame.grid(row=0, column=1, rowspan=2)

        self.top_frame = tk.Frame(self.frame)
        self.top_frame.grid(row=0, column=0)

        self.bottom_frame = tk.Frame(self.frame)
        self.bottom_frame.grid(row=1, column=0)

        self.status_frame = tk.Frame(self.frame)
        self.status_frame.grid(row=2, column=0, columnspan = 1)

        self.chart = FigureCanvasTkAgg(self.fig, self.top_frame)
        self.chart.get_tk_widget().grid()

    def draw(self):
        self.chart.draw()

    def close(self):
        self.frame.destroy()
        self.callback()


class SettingsWindow:

    def __init__(self, root, settings_template, callback, window=True):

        self.callback = callback
        self.settings_template = settings_template

        if window:
            self.frame = tk.Toplevel(root)
            self.button_frame = tk.Frame(self.frame)
            self.button_frame.pack(side="bottom")
        else:
            self.frame = tk.Frame(root)
            self.frame.pack()
            self.button_frame = tk.Frame(self.frame)

        self.settings_frame = tk.Frame(self.frame)
        self.settings_frame.pack(side="top")

        self.settings = create_setting_widgets(settings_template)

        if isinstance(self.settings_template, dict):
            self.settings.create_widgets(self.settings_frame)


        elif isinstance(self.settings_template, list):
            for s in self.settings:
                s.create_widgets(self.settings_frame)

        exit_button = tk.Button(self.button_frame, text="Exit", command=self.close)
        exit_button.pack(side="right")

        apply_button = tk.Button(self.button_frame, text="Apply", command=self.apply)
        apply_button.pack(side="right")

        save_button = tk.Button(self.button_frame, text="Save", command=self.save)
        save_button.pack(side="right")

    def lock(self):
        self.settings.lock()

    def unlock(self):
        self.settings.unlock()

    def close(self):

        self.frame.destroy()

    def save(self):
        if self.apply():
            self.close()

    def apply(self):

        if isinstance(self.settings_template, dict):
            # self.settings.make_values()
            export = self.settings.export_settings()
            if not export:
                return False

        elif isinstance(self.settings_template, list):
            export = []
            for s in self.settings:
                s.make_values()

                export.append(s.export_settings())

        if None in export:
            return False

        self.callback(export)
        return True


class ListSettingsWindow(SettingsWindow):

    def __init__(self, root, settings_template, callback):

        self.callback = callback
        self.settings_template = settings_template

        self.frame = tk.Toplevel(root)
        self.top_frame = tk.Frame(self.frame)
        self.top_frame.pack(side="top")

        self.settings_frame = tk.Frame(self.top_frame)
        self.settings_frame.pack(side="right")

        self.listbox_frame = tk.Frame(self.top_frame)
        self.listbox_frame.pack(side="left", fill="y", expand=True)

        self.button_frame = tk.Frame(self.frame)
        self.button_frame.pack(side="bottom")

        self.settings = create_setting_widgets(settings_template)

        for i in self.settings:
            i.create_widgets(self.settings_frame, pack=False)

        setting_names = [i.get_experiment_variables().get_variable("name") for i in self.settings]

        self.listbox = tk.Listbox(self.listbox_frame)
        for name in setting_names:
            self.listbox.insert(tk.END, name)
        self.listbox.bind("<<ListboxSelect>>", self.update_selection)
        self.listbox.pack(fill="y", expand=True)

        self.settings[0].show_widgets()

        exit_button = tk.Button(self.button_frame, text="Exit", command=self.close)
        exit_button.pack(side="right")

        apply_button = tk.Button(self.button_frame, text="Apply", command=self.apply)
        apply_button.pack(side="right")

        save_button = tk.Button(self.button_frame, text="Save", command=self.save)
        save_button.pack(side="right")

    def update_selection(self, event):

        sel = self.listbox.curselection()
        i = 0 if len(sel) == 0 else sel[0]

        for setting in self.settings:
            setting.hide_widgets()

        self.settings[i].show_widgets()

    def close(self):

        self.frame.destroy()

    def apply(self):

        export = []
        for s in self.settings:
            s.make_values()
            export.append(s.export_settings())

        self.callback(export)


def get_simple_setting(k, v):
    return MySetting(k, v)


def get_dict_setting(k, v):
    if len(v.values()) == 1:
        v = list(v.items())[0]
        setting = get_simple_setting(v[0], v[1])

    else:
        value = v["value"] if "value" in v else 0

        setting = MySetting(k, value, **v)
        setting.randomizable = v["randomizable"] if "randomizable" in v else False
        t = v["type"]
        if t == "int":
            setting.type = int
        elif t == "float":
            setting.type = float
        elif t == "bool":
            setting.type = bool
        elif t == "str":
            setting.type = str
        elif t == "file" or t == "saveas":
            setting.type = t
            if "filetypes" in v:
                setting.filetypes = v["filetypes"]
        elif t == "color":
            setting.type = "color"
        else:
            raise Exception

    return setting


def get_group_setting(k, v):
    setting_group = MySettingGroup(k, group_settings=v[0])

    for s in v[1:]:
        name = list(s.keys())[0]
        value = list(s.values())[0]
        setting = get_single_setting(name, value).settings[0]

        setting_group.append_setting(setting)

    return setting_group


def get_single_setting(k, v):
    setting_group = MySettingGroup(k)

    if isinstance(v, dict):

        setting = get_dict_setting(k, v)
        setting_group.append_setting(setting)

    else:
        setting = get_simple_setting(k, v)
        setting_group.append_setting(setting)

    return setting_group


def create_setting_widgets(settings_dict):
    """input may be a list"""

    if isinstance(settings_dict, dict):
        return create_single_settings_widget(settings_dict)

    elif isinstance(settings_dict, list):
        result = []
        for d in settings_dict:
            result.append(create_single_settings_widget(d))
        return result


def create_single_settings_widget(settings_dict):
    trail_settings = MyTrialSettings()

    for k, v in settings_dict.items():

        if isinstance(v, list):
            setting_group = get_group_setting(k, v)
            trail_settings.append_group(setting_group)

        else:

            trail_settings.append_group(get_single_setting(k, v))

    return trail_settings
