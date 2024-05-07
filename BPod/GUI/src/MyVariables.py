import os
import tkinter as tk
import tkinter.ttk as ttk

import numpy as np
import pandas as pd
from sympy import Eq, sympify, solveset, lambdify


class CallMethod():
    EXPERIMENT = 0
    TRIAL = 1


class MyVariable():

    def __init__(self, name, type, **kwargs):
        self.name = name
        self.type = type
        self.inferred = False
        self.parameters = {}

    def get_parameters(self):
        return {}

    def get_value(self, **kwargs):

        if self.inferred:
            free = list(self.free_symbols)
            free = [str(i) for i in free]
            fixed = {k: kwargs[k] for k in free}

            if None in fixed.values():
                return None
            else:
                return self.expression(**fixed)
        else:
            if hasattr(self, "value"):
                return self.value
            else:
                pass

    def _compute_value(self):
        pass


class MyConstant(MyVariable):

    def __init__(self, *args, **kwargs):

        self.call_method = CallMethod.EXPERIMENT
        super().__init__(*args, **kwargs)

    def set_value(self, value):

        if isinstance(value, self.type):
            self.value = value
        else:
            raise ValueError


class MyFile(MyConstant):

    def __init__(self, *args, **kwargs):
        self.call_method = CallMethod.EXPERIMENT
        super().__init__(*args, **kwargs)

    def set_value(self, value):
        self.value = value


class MyColor(MyConstant):

    def __init__(self, *args, **kwargs):
        self.call_method = CallMethod.EXPERIMENT
        super().__init__(*args, **kwargs)

    def set_value(self, value):
        self.value = value


class MyGenerator(MyVariable):

    def __init__(self, name, type, **kwargs):
        self.call_method = kwargs["call_method"] if "call_method" in kwargs else CallMethod.EXPERIMENT
        super().__init__(name, type, **kwargs)


class MyUniformRandomVariable(MyGenerator):

    def __init__(self, a, b, name, type, **kwargs):
        self.a = a
        self.b = b

        super().__init__(name, type, **kwargs)

        self.parameters = {"a": self.a, "b": self.b}

    def get_parameters(self):
        return self.parameters

    def generate_value(self, exp_time, trial_time):
        value = np.random.uniform(self.a, self.b)
        # if isinstance(value, self.type):
        self.value = value
        # else:
        #     try:
        #         self.value = self.type(value)
        #     except Exception:
        #         raise ValueError

        return self.value


class MyNormalRandomVariable(MyGenerator):

    def __init__(self, m, s, name, type, **kwargs):
        self.m = m
        self.s = s

        super().__init__(name, type, **kwargs)

        self.parameters = {"m": self.m, "s": self.s}

    def get_parameters(self):
        return self.parameters

    def generate_value(self, exp_time, trial_time):
        value = np.random.normal(self.m, self.s)
        # if isinstance(value, self.type):
        self.value = value
        # else:
        #     try:
        #         self.value = self.type(value)
        #     except Exception:
        #         raise ValueError

        return self.value


class MyExperimentVariables():
    def __init__(self):
        self.variables = []
        self.complete = True
        self.trial_index = 0
        self.dataframe = pd.DataFrame()

    def is_complete(self):
        if None in self.get_settings_dict().values():
            return False
        else:
            return True

    def append(self, variable):
        assert isinstance(variable, MyVariable)
        self.variables.append(variable)

    def join(self, experiment_variables):

        c = experiment_variables.complete
        self.complete = True if c and self.complete else False

        for v in experiment_variables.variables:
            self.append(v)

    def start_experiment(self):

        for v in self.variables:
            if isinstance(v, MyGenerator):
                if v.call_method == CallMethod.EXPERIMENT:
                    v.generate_value(0, 0)
                elif v.call_method == CallMethod.TRIAL:
                    v.generate_value(0, 0)

    def write_csv(self, path):

        df = self.dataframe
        df = df.append(self.get_settings_dict(), ignore_index=True)
        self.dataframe = df
        df.to_csv(os.path.join(path, "trial_variables.csv"))

    def start_trial(self, path=None):

        self.trial_index += 1

        exp_time = 0
        for v in self.variables:
            if isinstance(v, MyGenerator):
                if v.call_method == CallMethod.TRIAL:
                    v.generate_value(exp_time, 0)

        if path:
            self.write_csv(path)

    def has_variable(self, name):

        for v in self.variables:
            if v.name == name:
                return True

    def get_variable(self, name):

        fixed = self._get_fixed_dict()

        for v in self.variables:
            if v.name == name:
                return v.get_value(**fixed)

    def set_variable(self, name, value):

        for v in self.variables:
            if v.name == name and isinstance(v, MyConstant):
                return v.set_value(value)

    def _get_fixed_dict(self):

        result = {}
        for v in self.variables:
            if not v.inferred:
                result[v.name] = v.get_value()
        return result

    def _get_non_fixed_dict(self, fixed_variables):

        result = {}
        for v in self.variables:
            if v.inferred:
                result[v.name] = v.get_value(**fixed_variables)
        return result

    def get_settings_dict(self):

        fixed = self._get_fixed_dict()
        non_fixed = self._get_non_fixed_dict(fixed)
        fixed.update(non_fixed)

        return fixed


class MyTrialSettings():

    def __init__(self):
        self.setting_groups = []

    def lock(self):
        for g in self.setting_groups:
            g.lock()

    def unlock(self):
        for g in self.setting_groups:
            g.unlock()

    def export_settings(self):

        result = {}
        for group in self.setting_groups:
            result[group.name] = group.export_settings()

        if None in result.values():
            return False
        else:
            return result

    def append_group(self, settings_group):

        assert isinstance(settings_group, MySettingGroup)
        self.setting_groups.append(settings_group)

    def remove_group(self, name):

        for group in self.setting_groups:
            if group.name == name:
                self.setting_groups.remove(group)

    def hide_widgets(self):

        self.canvas.pack_forget()
        self.scroll_y.pack_forget()

    def show_widgets(self):

        self.scroll_y.pack(fill='y', expand = True, side='right')
        self.canvas.pack(expand = True,fill = "y")

    def create_widgets(self, root, pack=True):

        canvas = tk.Canvas(root)
        self.canvas = canvas

        scroll_y = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
        self.scroll_y = scroll_y

        frame = tk.Frame(canvas)


        self.frame = frame

        for group in self.setting_groups:
            group.get_widgets(frame)

        self.canvas.create_window(0,0, window=self.frame)


        self.update()

        if pack:
            self.show_widgets()

    def update(self):


        bbox = self.canvas.bbox("all")

        self.canvas.configure(
            width = bbox[2] - bbox[0],
            height = bbox[3] - bbox[1]
        )

        self.canvas.update_idletasks()

        self.canvas.configure(
            scrollregion=self.canvas.bbox('all'),
                              yscrollcommand=self.scroll_y.set)

        self.canvas.after(100, self.update)

    def make_values(self):

        for group in self.setting_groups:
            group.make_values()

    def get_experiment_variables(self):

        experiment_variables = MyExperimentVariables()

        for group in self.setting_groups:
            experiment_variables.join(group.get_experiment_variables())

        return experiment_variables


class MySettingGroup():

    def __init__(self, name, group_settings={}):
        self.name = name
        self.label = group_settings["label"] if "label" in group_settings else name
        self.settings = []
        self.group_settings = group_settings

    def lock(self):
        for s in self.settings:
            s.lock()

    def unlock(self):
        for s in self.settings:
            s.unlock()

    def get_experiment_variables(self):

        experiment_variables = MyExperimentVariables()
        complete = True

        if not self.is_consistient():
            return False

        elif not self.is_complete():
            complete = False
        else:
            self.make_values()
            for variable in self.get_variables():
                if not variable is None:
                    experiment_variables.append(variable)

        experiment_variables.complete = complete
        return experiment_variables

    def get_variable_list(self):

        variable_list = []

        if not self.is_complete():
            return False
        else:
            self.make_values()
            for variable in self.get_variables():
                if not variable is None:
                    variable_list.append(variable)

        return variable_list

    def export_settings(self):

        def export_single_setting(setting):

            setting_parameter = setting.parameters
            variable = setting.variable

            constant = not setting.randomizable

            setting_type = setting.type.__name__ if isinstance(setting.type, type) else setting.type
            variable_type = variable.type.__name__ if isinstance(variable.type, type) else variable.type

            if isinstance(setting.variable, MyGenerator):
                variable_parameters = variable.parameters
                result = variable_parameters

                i = np.where(GENERATORS[:, 1] == type(setting.entry_widget))[0][0]
                result["entry_type"] = GENERATORS[i, 0]
                if not result["entry_type"] == GENERATORS[0, 0]:
                    result["randomizable"] = True

                result["call_method"] = setting.variable.call_method
                result["type"] = str(variable_type)
            else:
                if variable.inferred:
                    value = None
                else:
                    value = variable.get_value()

                if not constant:

                    if setting_parameter:
                        result = setting_parameter
                        result.update({"value": value})

                    else:
                        result = value

                elif constant:

                    if setting_parameter:
                        result = setting_parameter
                        result.update({"value": value})
                    else:
                        result = {"value": value, "type": str(setting_type), "randomizable": str(setting.randomizable)}

            return result

        if not self.check_group():
            return None

        elif len(self.settings) == 0:
            return None

        elif len(self.settings) == 1:

            self.make_values()
            result = export_single_setting(self.settings[0])

        else:

            self.make_values()
            result = [self.group_settings]
            for setting in self.settings:
                entry = export_single_setting(setting)
                result.append({setting.name: entry})

        return result

    def append_setting(self, settings):

        assert isinstance(settings, MySetting)
        self.settings.append(settings)

    def get_variables(self):
        variables = []
        for setting in self.settings:
            variables.append(setting.variable)

        return variables

    def has_setting(self, name):

        for setting in self.settings:
            if setting.name == name:
                return True

        return False

    def get_setting(self, name):
        for setting in self.settings:
            if setting.name == name:
                return setting

        return False

    def get_defining_equation(self):

        if hasattr(self, "group_settings"):
            if "rhs" in self.group_settings and "lhs" in self.group_settings:
                rhs = self.group_settings["rhs"]
                lhs = self.group_settings["lhs"]
                eq = Eq(sympify(lhs), sympify(rhs))

                return eq

        return None

    def solve_for(self, name):

        eq = self.get_defining_equation()

        return solveset(eq, name)

    def get_empty_settings(self):

        result = []
        for setting in self.settings:
            if setting.is_empty():
                result.append(setting)

        return result

    def mark_incomplete(self, ):

        if hasattr(self, "frame"):
            self.frame.config(
                highlightthickness=2,
                highlightbackground="red",
                highlightcolor="red"
            )

    def mark_complete(self, ):

        if hasattr(self, "frame"):
            self.frame.config(
                highlightthickness=0,
                highlightbackground="red",
                highlightcolor="red"
            )

    def has_equation(self):

        if hasattr(self, "group_settings"):
            if "rhs" in self.group_settings and "lhs" in self.group_settings:
                return True

        return False

    def is_complete(self):

        if not self.group_settings:
            for setting in self.settings:
                if setting.is_empty():
                    self.mark_incomplete()
                    return False
                else:
                    self.mark_complete()

            return True
        else:
            for setting in self.settings:

                if setting.is_empty():
                    name = setting.name
                    sol = self.solve_for(name)

                    free_symbols = list(sol.free_symbols)

                    for symbol in list(sol.free_symbols):
                        symbol_setting = self.get_setting(str(symbol))
                        if not symbol_setting.is_empty():
                            free_symbols.remove(symbol)

                    if not len(free_symbols) == 0:
                        free_symbols.append(sympify(setting.name))
                        self.mark_incomplete()
                        return False
                    else:
                        self.mark_complete()
                        continue
            return True

    def make_values(self):

        if not self.group_settings or not self.has_equation():
            for setting in self.settings:
                setting.save()
            return True
        else:
            for setting in self.settings:
                if setting.is_empty():
                    name = setting.name
                    sol = self.solve_for(name)

                    for symbol in list(sol.free_symbols):
                        symbol_setting = self.get_setting(str(symbol))
                        if not symbol_setting.randomizable:
                            symbol_setting.save()
                            symbol_variable = symbol_setting.variable
                            sol = sol.subs(symbol_setting.name, symbol_variable.get_value())

                    setting.save(expression=sol.sup)
                else:
                    setting.save()

    def mark_consistient(self):
        self.mark_complete()

    def mark_inconsistient(self):
        if hasattr(self, "frame"):
            self.frame.config(
                highlightthickness=2,
                highlightbackground="blue",
                highlightcolor="blue"
            )

    def is_consistient(self):

        result = True

        if not self.group_settings or not self.has_equation():
            self.mark_consistient()
            result = True
        else:

            random = False
            eq = self.get_defining_equation()

            from sympy import simplify
            eq = simplify(eq)

            for symbol in list(eq.free_symbols):

                symbol_setting = self.get_setting(str(symbol))

                if symbol_setting.is_constant():
                    symbol_setting.save()
                    symbol_variable = symbol_setting.variable
                    eq = eq.subs(symbol_setting.name, symbol_variable.get_value())
                else:
                    random = True

            if not random:
                if len(list(eq.free_symbols)) > 0:
                    self.mark_consistient()
                    result = True

                elif eq:
                    self.mark_consistient()
                    result = True
                else:
                    self.mark_inconsistient()
                    result = False
            else:
                empty_settings = np.array([i.is_empty() for i in self.settings])

                if np.count_nonzero(empty_settings) > 0:
                    self.mark_consistient()
                    result = True
                else:
                    self.mark_inconsistient()
                    result = False

        if result:
            self.mark_consistient()
        else:
            self.mark_inconsistient()

        return result

    def check_group(self):

        if not self.is_complete():
            return False

        elif not self.is_consistient():
            return False

        else:
            return True

    def has_visible_settings(self):

        for setting in self.settings:
            if not setting.hide:
                return True

        return False

    def count_visible_settings(self):
        i = 0

        for setting in self.settings:
            if not setting.hide:
                i += 1

        return i

    def get_widgets(self, root):


        frame = tk.Frame(root, pady=4)
        if self.has_visible_settings():
            frame.pack(side="top")

        self.frame = frame

        show_label = True if self.count_visible_settings() > 1 else False
        if not show_label:
            self.label = self.settings[0].label

        from tkinter import font
        f = font.nametofont(font.names()[7])

        group_label = tk.Label(frame, text=self.label, font=(f, 10, "bold"))

        sep1 = ttk.Separator(frame)
        sep2 = ttk.Separator(frame)

        if not (len(self.settings) == 1 and self.settings[0].hide):
            sep1.pack(side="top", fill=tk.X)
            group_label.pack(side="top")

            sep2.pack(side="top", fill=tk.X)

        for setting in self.settings:
            setting.make_header_widgets(frame, show_label=show_label)

        sep3 = ttk.Separator(frame)

        if not (len(self.settings) == 1 and self.settings[0].hide):
            sep3.pack(side="bottom", fill=tk.X)


class MySetting():
    header_width = 1

    def __init__(self, name, default, **kwargs):

        self.name = name
        self.default = default  # 1 if default is None else default
        self.label = kwargs["label"] if "label" in kwargs else name
        self.type = type(default)
        self.tooltip = ""
        self.randomizable = False

        self.variable = None
        self.widgets = {}
        self.parameters = kwargs

        if "hide" in kwargs:
            self.hide = kwargs["hide"]
        else:
            self.hide = False

    def lock(self):

        self.entry_widget.lock()

    def unlock(self):

        self.entry_widget.unlock()


    def is_constant(self):

        entry_type = self.get_entry_type()
        if entry_type == GENERATORS[0, 0]:
            return True
        else:
            False

    def is_empty(self):

        return self.entry_widget.is_empty()

    def set(self, value):

        self.entry_widget.set(value)

    def update_widgets(self, event):

        for widget in self.entry_frame.winfo_children():
            widget.pack_forget()

        self.make_entry_widgets()

    def make_header_widgets(self, root, show_label=True):



        frame = tk.Frame(root)
        if not self.hide:
            frame.pack()
        self.frame = frame

        # frame.grid_columnconfigure(1, pad=50)
        # frame.grid_columnconfigure(0, minsize=100)

        self.header_frame = tk.Frame(frame, width=self.header_width)
        # c = root.grid_size()[1]+1
        # frame.grid_rowconfigure(c,pad = 20)

        # self.header_frame.grid(row = c, column = 0)
        self.header_frame.pack(side="left", pady=2)

        self.entry_frame = tk.Frame(self.frame)
        # self.entry_frame.grid(row = c, column = 1)
        self.entry_frame.pack(side="right")

        label = tk.Label(self.header_frame, text=self.label)
        if show_label:
            label.pack(side="top")

        box = ttk.Combobox(self.header_frame, state="readonly")

        box.bind("<<ComboboxSelected>>", self.update_widgets)
        if self.randomizable:
            box["values"] = list(GENERATORS[:, 0])
            box.pack(side="bottom")
        else:
            box["values"] = GENERATORS[0, 0]

        entry_type = self.parameters["entry_type"] if "entry_type" in self.parameters else "constant"
        i = np.where(entry_type == GENERATORS[:, 0])[0][0]
        box.current(i)

        self.header_widgets = {
            "label": label,
            "box": box
        }

        self.make_entry_widgets()

    def get_entry_type(self):

        i = self.header_widgets["box"].current()
        entry_type = self.header_widgets["box"]["value"][i]
        return entry_type

    def make_entry_widgets(self):

        entry_type = self.get_entry_type()
        frame = self.entry_frame
        purge_old_variables = False
        for w in frame.winfo_children():
            w.pack_forget()

        if hasattr(self, "entry_widget"):
            purge_old_variables = True
            old_variable = self.entry_widget.get()
            old_keys = list(old_variable.parameters.keys())
            if "entry_type" in self.parameters:
                del self.parameters["entry_type"]

        if entry_type == GENERATORS[0, 0]:
            if "call_method" in self.parameters:
                del self.parameters["call_method"]

            self.randomizable = False
            if self.type == "file":
                entry = FileEntry(frame, self.name, default=self.default)
                if hasattr(self, "filetypes"):
                    entry.filetypes = self.filetypes
            elif self.type == "saveas":
                entry = SaveAsEntry(frame, self.name, default=self.default)
                if hasattr(self, "filetypes"):
                    entry.filetypes = self.filetypes
            elif self.type == "color":
                entry = ColorEntry(frame, self.name, default=self.default)

            else:

                if self.default is None:
                    entry = ConstantEntry(frame, self.name, default="", type=self.type, dummy=True)
                else:
                    entry = ConstantEntry(frame, self.name, default=self.default, type=self.type)

        else:
            available_types = GENERATORS[:, 0]
            if entry_type in available_types:
                i = np.where(entry_type == available_types)[0][0]
                entry = GENERATORS[i, 1](frame, self.name, self.type, **self.parameters)

        if purge_old_variables:

            new_keys = entry.get().parameters.keys()

            for k in old_keys:
                if k not in new_keys:
                    if k in self.parameters:
                        del self.parameters[k]

        self.entry_widget = entry

    def save(self, expression=None):

        entry_type = self.get_entry_type()
        entry_widget = self.entry_widget
        variable = entry_widget.get()

        if expression:
            f = lambdify(expression.free_symbols, expression, "numpy")

            variable.inferred = True
            variable.free_symbols = expression.free_symbols
            variable.expression = f
            if len(variable.free_symbols) == 0:
                self.set(variable.get_value())

        self.variable = variable


class MyCompoundWidget:
    standard_width = 15
    standard_width_small = 3

    def lock(self):
        self.v["state"] = "disabled"

    def unlock(self):
        self.v["state"] = "normal"



    def is_empty(self):
        return False

    def set(self, value):
        pass

    def get_call_method_box(self, frame, **kwargs):
        tk.Label(frame, text="randomize per").pack()
        method_box = ttk.Combobox(frame, state="readonly", width=5)
        method_box["values"] = ["exp", "trial"]

        call_method = kwargs["call_method"] if "call_method" in kwargs else CallMethod.TRIAL
        method_box.current(call_method)
        method_box.pack()
        return method_box


class ConstantEntry(MyCompoundWidget):

    def __init__(self, frame, name, default=0, type=float, dummy=False, **kwargs):

        self.name = name
        self.type = type
        self.default = default
        self.dummy = dummy

        if type == float:
            self.make_float_entry(frame)
        elif type == int:
            self.make_int_entry(frame)
        elif type == bool:
            self.make_bool_entry(frame)
        else:
            self.make_string_entry(frame)

    def lock(self):

        self.v["state"] = "disabled"

    def unlock(self):
        self.v["state"] = "normal"

    def user_enter(self, event):

        if not self.v.get() == "":
            self.dummy = False

    def set(self, value):

        if self.type == float:
            self.v.delete(0, tk.END)
            self.v.insert(0, str(value))

    def make_float_entry(self, frame):

        self.v = tk.Entry(frame, width=self.standard_width)
        if not self.default == "":
            self.v.delete(0, tk.END)
            self.v.insert(0, str(self.default))
        self.v.bind("<Button-1>", self.user_enter)
        self.v.pack()

    def make_int_entry(self, frame):

        self.v = tk.Scale(frame, from_=0, to=20, orient="horizontal")
        self.v.set(self.default)
        self.v.pack()

    def make_bool_entry(self, frame):
        self.v = MyCombobox(frame)
        self.v.set_values([
            [self.default, not self.default],
            [str(self.default), str(not self.default)]
        ])

        self.v.current(0)
        self.v.pack()

    def make_string_entry(self, frame):

        self.v = tk.Entry(frame, width=self.standard_width)
        self.v.delete(0, tk.END)
        self.v.insert(0, str(self.default))
        self.v.pack()

    def get_entry_value(self):

        if self.dummy:
            v = self.default
        else:
            v = self.v.get()
        return v

    def is_empty(self):

        value = self.get_entry_value()

        if value == "":
            return True
        else:
            return False

    def get(self, expression=None):

        variable = MyConstant(self.name, self.type)

        if not self.is_empty():
            value = variable.type(self.v.get())
            variable.set_value(value)

        return variable


class FileEntry(MyCompoundWidget):

    def __init__(self, frame, name, default=""):

        self.frame = frame
        self.name = name
        self.default = default
        self.filetypes = [("All Files", "*")]

        self.v = tk.Entry(frame, width=self.standard_width)
        self.v.delete(0, tk.END)
        self.v.insert(0, str(default))
        self.v.pack()

        tk.Button(frame, text="select file", command=self.ask_file).pack()

    def ask_file(self):

        initialdir = "."

        from os import path

        if "/" in self.v.get():
            initialdir = path.dirname(self.v.get())

        file = tk.filedialog.askopenfile(
            filetypes=self.filetypes,
            initialdir=initialdir
        )

        if not file is None:
            self.v.delete(0, tk.END)
            self.v.insert(0, file.name)

    def get(self):

        variable = MyFile(self.name, str)
        value = self.v.get()
        variable.set_value(value)

        return variable


class SaveAsEntry(MyCompoundWidget):

    def __init__(self, frame, name, default=""):

        self.frame = frame
        self.name = name
        self.default = default
        self.filetypes = [("All Files", "*")]

        self.v = tk.Entry(frame, width=self.standard_width)
        self.v.delete(0, tk.END)
        self.v.insert(0, str(default))
        self.v.pack()

        tk.Button(frame, text="select file", command=self.ask_file).pack()

    def ask_file(self):

        initialdir = "."

        from os import path

        if "/" in self.v.get():
            initialdir = path.dirname(self.v.get())

        file = tk.filedialog.asksaveasfilename(
            filetypes=self.filetypes,
            initialdir=initialdir
        )

        if not file is None:
            self.v.delete(0, tk.END)
            self.v.insert(0, file)

    def get(self):

        variable = MyFile(self.name, str)
        value = self.v.get()
        variable.set_value(value)

        return variable


class UniformEntry(MyCompoundWidget):

    def __init__(self, frame, name, setting_type, a=0, b=1, **kwargs):
        self.name = name
        self.type = setting_type

        a_frame = tk.Frame(frame)
        a_frame.pack()

        b_frame = tk.Frame(frame)
        b_frame.pack()

        tk.Label(a_frame, text="a").pack(side="left")
        tk.Label(b_frame, text="b").pack(side="left")

        self.a = tk.Entry(a_frame, width=self.standard_width_small)
        self.b = tk.Entry(b_frame, width=self.standard_width_small)

        self.a.delete(0, tk.END)
        self.a.insert(0, str(a))

        self.b.delete(0, tk.END)
        self.b.insert(0, str(b))

        self.a.pack(side="right")
        self.b.pack(side="right")

        self.method_box = self.get_call_method_box(frame, **kwargs)

    def get(self):

        a = float(self.a.get())
        b = float(self.b.get())

        variable = MyUniformRandomVariable(a, b, self.name, self.type)

        if self.method_box.get() == "trial":
            variable.call_method = CallMethod.TRIAL
        else:
            variable.call_method = CallMethod.EXPERIMENT

        return variable


class NormalEntry(MyCompoundWidget):

    def __init__(self, frame, name, setting_type, m=0, s=1, **kwargs):
        self.name = name
        self.type = setting_type

        a_frame = tk.Frame(frame)
        a_frame.pack()

        b_frame = tk.Frame(frame)
        b_frame.pack()

        tk.Label(a_frame, text="m").pack(side="left")
        tk.Label(b_frame, text="s").pack(side="left")

        self.m = tk.Entry(a_frame, width=self.standard_width_small)
        self.s = tk.Entry(b_frame, width=self.standard_width_small)

        self.m.delete(0, tk.END)
        self.m.insert(0, str(m))

        self.s.delete(0, tk.END)
        self.s.insert(0, str(s))

        self.m.pack(side="right")
        self.s.pack(side="right")

        self.method_box = self.get_call_method_box(frame, **kwargs)

    def get(self):

        m = float(self.m.get())
        s = float(self.s.get())

        variable = MyNormalRandomVariable(m, s, self.name, self.type)

        if self.method_box.get() == "trial":
            variable.call_method = CallMethod.TRIAL
        else:
            variable.call_method = CallMethod.EXPERIMENT

        return variable


class ColorEntry(MyCompoundWidget):

    def __init__(self, frame, name, default="red"):
        self.frame = frame
        self.name = name
        self.default = default

        self.v = tk.Entry(frame, width=self.standard_width)
        self.v.pack()
        self.v.delete(0, tk.END)
        self.v.insert(0, str(default))

        tk.Button(frame, text="select color", command=self.ask_color).pack()

    def ask_color(self):
        from tkinter.colorchooser import askcolor
        result = askcolor()
        self.v.delete(0, tk.END)
        self.v.insert(0, str(result[1]))

    def get(self):
        variable = MyColor(self.name, str)
        value = self.v.get()
        variable.set_value(value)

        return variable


class MyCombobox:

    def __init__(self, frame):
        self.box = ttk.Combobox(frame)
        self.values = []

    def set_values(self, values):
        self.values = values

        self.box["values"] = self.values[1]

    def pack(self, **kwargs):
        self.box.pack(kwargs)

    def current(self, i):
        self.box.current(i)

    def get(self):
        v = self.box.get()

        i = self.values[1].index(v)
        return self.values[0][i]


GENERATORS = np.array([
    ["constant", MyConstant],
    ["uniform_float", UniformEntry],
    ["normal_float", NormalEntry]
])
