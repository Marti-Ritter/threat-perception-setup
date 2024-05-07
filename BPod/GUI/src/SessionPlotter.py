import json
import os
from copy import deepcopy

import matplotlib as mpl
import numpy as np
import pandas as pd
from matplotlib import cm


class SessionPlotter:

    def __init__(self,loader):

        assert isinstance(loader,SessionLoader)
        self.loader = loader

    def get_event_color(self, event):

        trans = True if int(event["transition"] == 1) else False
        success = True if event["type"] == "success" else False
        challenge = True if event["type"] in ("success", "fail") else False
        buffer = True if event["type"] == "buffer" else False

        success_color = self.settings["success_color"]
        fail_color = self.settings["fail_color"]
        desaturation = self.settings["desaturation"]

        a = 1
        if success:
            color = success_color
        else:
            color = fail_color

        if isinstance(color, str):
            color = mpl.colors.to_rgb(color)

        color = mpl.colors.rgb_to_hsv(color)

        if buffer and not trans:
            color[1] -= desaturation
        elif trans and not challenge:
            a = 0

        rgb = mpl.colors.hsv_to_rgb(color)

        return (rgb[0], rgb[1], rgb[2], a)

    def get_event_marker(self, event):

        if event["+INFO"] == "Tup":
            return "."
        else:
            return "+"

    def plot_event(self, event, h, ax):

        p = [event["PC-TIME"], h]

        c = self.get_event_color(event)
        a = c[3]
        c = c[0:3]

        m = self.get_event_marker(event)

        ax.scatter(p[0], p[1], color=c, marker=m, zorder=2, s=100, alpha=a)

        return None

    def plot_trial(self, trial_df, trial_index, ax):

        # dataframes = self.extract_dataframes(trial_df)
        # self.append_dataframes(trial_index,dataframes)
        dataframes = deepcopy(self.loader.dataframes)
        for k, df in dataframes.items():
            dataframes[k] = df.loc[df["trial_index"] == trial_index]

        states = dataframes["states"]
        self.loader.add_state_names(states["state_name"])

        path = dataframes["path"]
        events = dataframes["events"]
        # events = self.get_event_type(events,self.trial_indices[trial_index])
        self.loader.add_event_names(events["+INFO"])

        color_dict = {}
        cmap = cm.get_cmap("Dark2")

        for i, state in enumerate(states["state_name"].unique()):
            color_dict[state] = cmap(i)
            bar = mpl.patches.Rectangle((0, 0), height=0.1, width=0.1, color=cmap(i))
            self.loader.collect_states.update({state: bar})

        path_list = [r[1] for r in path.iterrows()]
        events = self.loader.get_transition_events(path_list, events)

        for i, s in enumerate(path_list):

            if i == len(path) - 1:
                break

            h = self.settings["state_bar_height"]
            w = path_list[i + 1]["PC-TIME"] - s["PC-TIME"]

            o = (s["PC-TIME"], self.get_trial_lanes()[self.loader.trial_indices[trial_index]] - h / 2)
            c = self.get_state_color(s["state_name"])

            bar = mpl.patches.Rectangle(o, height=h, width=w, color=c)
            ax.add_artist(bar)

        for i, event in events.iterrows():
            h = self.get_trial_lanes()[self.loader.trial_indices[event["trial_index"]]]
            h = h - self.settings["state_bar_height"]
            self.plot_event(event, h, ax)

        ax.set_xlim([0, 1.2 * (w + o[0])])
        ax.set_ylim((self.settings["ymin"], self.settings["ymax"]))

    def make_legend(self, ax):

        ax.clear()
        ax.axis("off")
        h = []
        l = []

        h.append(mpl.lines.Line2D([0], [0], markersize=0, color="w"))
        l.append("States")

        for k, v in self.loader.collect_states.items():
            h.append(v)
            l.append(k)

        h.append(mpl.lines.Line2D([0], [0], markersize=0, color="w"))
        l.append("Event Type")

        collected_events = self.get_collected_events()
        for k, v in collected_events[0].items():
            h.append(v)
            l.append(k)

        h.append(mpl.lines.Line2D([0], [0], markersize=0, color="w"))
        l.append("Success/Failure")

        for k, v in collected_events[1].items():
            h.append(v)
            l.append(k)
        ax.legend(h, l)

        h.append(mpl.lines.Line2D([0], [0], markersize=0, color="w"))
        l.append("Shade")

        for k, v in collected_events[2].items():
            h.append(v)
            l.append(k)

        ax.legend(h, l)

    def plot_session(self, ax):

        ax.clear()

        for i, t in enumerate(self.loader.dataframes["states"]["trial_index"].unique()):
            self.plot_trial(t, i, ax)

        ax.set_xlabel("time (s)")

        ticks = []
        labels = []

        versions = deepcopy(self.loader.trial_versions)

        for i, v in enumerate(versions):
            labels.append(v["name"])
            ticks.append(self.get_trial_lanes()[i])
        # ax.set_yticks(ticks)
        # ax.set_yticklabels(labels)

        ax.set_xlim(self.get_xlim())

    def get_xlim(self):

        time = self.loader.time
        w = self.settings["plot_window"]

        if time > w:

            return ([time - w, time + w * 0.2])
        else:
            return ([0, w])

    def plot_success_histogram(self, ax):
        import seaborn as sns
        ax.clear()
        df = self.loader.dataframes["states"]
        path = self.loader.dataframes["path"]
        success = path.groupby("trial_index").apply(lambda x: "success" in x["state_name"].unique())

        df = df.loc[df["state_name"] == "img_challenge"]
        df = df.set_index("trial_index", drop=False)
        df["success"] = success

        time_success = df.loc[df["success"], "total_time"]

        time_fail = df.loc[df["success"] == False, "total_time"]

        sns.distplot(time_success, ax=ax, kde=False, bins=self.settings["hist_bins"], color="green")
        sns.distplot(time_fail, ax=ax, kde=False, bins=self.settings["hist_bins"], color="red")

        ax.set_xlabel("time spent in img challenge")
        ax.set_ylabel("Absolute frequency")

    def plot_experiment(self, subplot_ax):

        if self.settings is None:
            self.load_settings()
        if hasattr(self.loader, "trial_list") and hasattr(self.loader, "trial_indices") and hasattr(self.loader, "trial_versions"):
            self.loader.save()
            if len(self.loader.trial_indices) > 0:
                #self.loader.write_dataframes()
                self.plot_session(subplot_ax["session"])
                self.make_legend(subplot_ax["legend"])
                self.plot_success_histogram(subplot_ax["hist"])

        pass

    def get_collected_events(self):
        markers = []
        marker_labels = []

        success = self.settings["success_color"]
        fail = self.settings["fail_color"]

        if isinstance(success, str):
            success = mpl.colors.to_rgb(success)

        if isinstance(fail, str):
            fail = mpl.colors.to_rgb(fail)

        r = 20
        for name in self.loader.event_names:
            event = pd.Series([name], ["+INFO"])
            marker_labels.append(name)
            marker = self.get_event_marker(event)
            marker = mpl.lines.Line2D([0], [0], marker=marker, color='w', markerfacecolor="black", markersize=r)
            markers.append(marker)

        desat = mpl.colors.rgb_to_hsv(success)
        desat[1] -= self.settings["desaturation"]

        desat = mpl.colors.hsv_to_rgb(desat)
        #
        colors = []
        color_labels = []
        for c in [success, fail]:
            colors.append(
                mpl.lines.Line2D([0], [0], marker=".", color='w', markerfacecolor=c, markersize=r)
            )

        for name in ["success", "failure"]:
            color_labels.append(name)

        shades = []
        shade_labels = []
        for c in [success, desat]:
            shades.append(
                mpl.lines.Line2D([0], [0], marker=".", color='w', markerfacecolor=c, markersize=r)
            )

        for name in ["transition", "challenge"]:
            shade_labels.append(name)

        result = [
            {marker_labels[i]: markers[i] for i in range(len(markers))},
            {color_labels[i]: colors[i] for i in range(len(colors))},
            {shade_labels[i]: shades[i] for i in range(len(shades))},
        ]
        return result

    def get_trial_lanes(self):

        n = len(np.unique(self.loader.trial_indices))

        m = self.settings["margin"]

        ymin = self.settings["ymin"]
        ymax = self.settings["ymax"]
        r = ymax - ymin

        ymin = ymin + r * m
        ymax = ymax - r * m

        return np.linspace(ymin, ymax, n)

    def get_state_color(self, state):

        cmap = cm.get_cmap("Dark2")
        color_dict = {}
        for i, state_name in enumerate(self.loader.state_names):
            color_dict[state_name] = cmap.colors[i]
        return color_dict[state]

class SessionLoader:

    def __init__(self):

        self.path = "./sessions/plotter_output/"
        self.state_names = []
        self.event_names = []
        self.settings = None
        self.collect_states = {}  # for legend creation
        self.collect_events = {}
        self.time = 0

    def save(self):

        return None
        self.path = self.output_settings.get_experiment_variables().get_variable("path")
        os.makedirs(self.path, exist_ok=True)

        if hasattr(self, "trial_versions"):
            with open(os.path.join(self.path, "trial_versions.json"), mode="w") as f:
                json.dump(self.trial_versions, f)
        if hasattr(self, "trial_indices"):
            with open(os.path.join(self.path, "trial_indices.json"), mode="w") as f:
                trial_indices = [int(i) for i in self.trial_indices]

                json.dump(trial_indices, f)

    def load(self):

        with open(os.path.join(self.path, "trial_versions.json"), mode="r") as f:
            self.trial_versions = json.load(f)

        with open(os.path.join(self.path, "trial_indices.json"), mode="r") as f:
            self.trial_indices = json.load(f)

    def get_trail_list(self, df):
        trials = self.get_trial_indices(df)
        df["PC-TIME"] = df["PC-TIME"].apply(pd.to_datetime)
        df["PC-TIME"] = df["PC-TIME"].sub(df.iloc[0]["PC-TIME"])
        df["PC-TIME"] = df["PC-TIME"].apply(lambda x: x.total_seconds())

        info = df.iloc[0:trials[0][0]]
        data = df.iloc[trials[0][0]:]

        trial_list = []

        for t in trials:
            trial = df.iloc[t[0]:t[1]]
            info = df.iloc[t[1]:t[2]]
            trial_list.append({
                "trial": trial,
                "info": info
            })

        return trial_list

    def get_trial_indices(self, df):

        trial_start = df.where(df["TYPE"] == "TRIAL")
        trial_end = df.where(df["TYPE"] == "END-TRIAL")

        trial_start = trial_start.dropna(how="all").index
        trial_end = trial_end.dropna(how="all").index + 1

        trial_end = np.array(trial_end.values)
        trial_start = np.array(trial_start.values)

        info_end = (trial_start)[1:]
        info_end = np.insert(info_end, len(info_end), len(df) - 1)

        return np.vstack([trial_start, trial_end, info_end]).T

    def extract_dataframes(self, trial_dict):

        trial_df = trial_dict["trial"]
        info_df = trial_dict["info"]

        trans = trial_df.where(trial_df["TYPE"] == "TRANSITION")
        trans = trans.dropna(how="all")
        trans = trans.drop(columns=trans.columns.drop(["PC-TIME", "MSG"]))
        trans = trans.set_index(pd.RangeIndex(len(trans)))

        events = trial_df.where(trial_df["TYPE"] == "EVENT")
        events = events.dropna(how="all")
        events = events.drop(columns=events.columns.drop(["PC-TIME", "MSG", "+INFO"]))
        events = events.set_index(pd.RangeIndex(len(events)))

        path = pd.DataFrame()

        for i, v in trans.iterrows():
            state = {
                "state_name": v["MSG"],
                "PC-TIME": v["PC-TIME"]
            }

            path = path.append(state, ignore_index=True)

        path = path.append({"state_name": "end_trial", "PC-TIME": trial_df.iloc[-1]["PC-TIME"]}, ignore_index=True)
        path = path.set_index(pd.RangeIndex(len(path)))

        states = pd.DataFrame()

        for i, v in info_df.loc[info_df["TYPE"] == "STATE"].iterrows():
            state = {
                "state_name": v["MSG"],
                "total_time": float(v["+INFO"])
            }
            states = states.append(state, ignore_index=True)

        states = states.dropna()

        result = {
            "path": path,
            "states": states,
            "transitions": trans,
            "events": events
        }
        return result

    def add_state_name(self, state):

        if not state in self.state_names:
            self.state_names.append(state)

    def add_state_names(self, states):
        for state in states:
            self.add_state_name(state)

    def add_event_name(self, event):

        if not event in self.event_names:
            self.event_names.append(event)

    def add_event_names(self, events):
        for event in events:
            self.add_event_name(event)

    def get_transition_events(self, path, events):

        event_times = events["PC-TIME"]  # [1:-1]
        path_times = [i["PC-TIME"] for i in path]

        events.insert(events.shape[1], "transition", pd.Series(np.zeros(len(events))))
        events.insert(events.shape[1], "type", pd.Series(["buffer"] * len(events)))

        for i in range(len(path_times) - 1):
            n0 = path_times[i]
            n1 = path_times[i + 1]

            s0 = path[i][1]
            s1 = path[i + 1][1]

            r = event_times[event_times.between(n0, n1)]
            if len(r) > 0:

                events.loc[events["PC-TIME"] == r.iloc[-1], "transition"] = 1
                if s0 == "img_challenge" or s0 == "img_wait":
                    events.loc[events["PC-TIME"] == r.iloc[-1], "type"] = s1
                else:
                    events.loc[events["PC-TIME"] == r.iloc[-1], "type"] = "buffer"

                # events.loc[events["PC-TIME"] == r.iloc[-1], "transition"] = 1

        return events

    def get_event_type(self, events, version_index):

        trial_version = self.trial_versions[version_index]
        result = pd.DataFrame()
        for i, event in events.iterrows():

            if event["+INFO"] == "Tup":
                t = trial_version["time_up_state"]
            else:
                t = trial_version["licking_state"]

            event["type"] = t
            result = result.append(event)

        return result

    def append_dataframes(self, i, dfs):

        for k, df in dfs.items():
            df["trial_index"] = i * np.ones(len(df), dtype=int)

            dfs[k] = df
        if not hasattr(self, "dataframes"):
            self.dataframes = dfs
        else:
            for k, df in dfs.items():
                self.dataframes[k] = self.dataframes[k].append(df)

    def load_settings(self):

        self.settings = self.plot_settings.get_experiment_variables().get_settings_dict()

    def load_session(self, path):
        try:
            df = pd.read_csv(path, sep=";", header=6)
            self.trial_list = self.get_trail_list(df)
        except:
            return False

        self.read_new_trials()

    def read_new_trials(self):

        if hasattr(self, "dataframes"):
            del self.dataframes

        for i, df in enumerate(self.trial_list):
            dataframes = self.extract_dataframes(df)
            self.append_dataframes(i, dataframes)

        time = df["trial"]["PC-TIME"].max()
        self.time = time

    def write_dataframes(self):

        for name, df in self.dataframes.items():
            with open(os.path.join(self.path, name + ".csv"), mode="w") as f:
                df.to_csv(f)

class TPMSessionLoad(SessionLoader):

    pass

class TPMSessionPlotter(SessionPlotter):

    def __init__(self,*args):

        super().__init__(*args)

        self.trace = np.array([
            np.linspace(0, self.loader.time, 100),
            np.random.lognormal(0, 0.2, 100) * 0.1
        ])
    def plot_trace(self,ax):

        ax.clear()
        ax.plot(self.trace[0],self.trace[1])
        ax.set_xlim(self.get_xlim())
