from pid import PidFile, PidFileError

from ui import UI


class Application:
    def __init__(self, alive_flag, window, current_output, process_names):
        self.alive_flag = alive_flag
        self.window = window
        self.window.resizable(0, 0)
        self.current_output = current_output
        self.process_names = process_names

        self.cams = [(process_id, name) for process_id, name in enumerate(self.process_names) if 'cam' in name]
        self.cam_labels = []
        self.mini_size = (190, 150)
        self.selected_cam = None
        self.selected_cam_frame = None
        self.selected_cam_label = None

        self.last_frame = time.perf_counter()

        self.create_widgets()
        self.alive_flag.wait()
        self.update()
        self.window.mainloop()

        self.pid_file = PidFile('Recorder')

    def create_widgets(self):
        for process_id, cam in self.cams:
            frame = tk.Frame(master=self.window, width=self.mini_size[0], height=self.mini_size[1])
            frame.grid_propagate(False)
            frame.grid(row=0, column=process_id)

            label = tk.Label(master=frame, bg='black', borderwidth=2)
            label.bind("<Button-1>", lambda e, x=process_id: self.select_window(x))
            label.pack(fill=tk.BOTH)
            self.cam_labels.append(label)

            new_frame = tk.Frame(master=frame)
            new_frame.place(x=2, y=2, anchor=tk.NW)
            tk.Label(master=new_frame, text=cam, bg='black', fg='white', font=("Helvetica", 16)).pack()

            self.selected_cam_frame = tk.Label(master=self.window, width=self.mini_size[0] * 3,
                                               height=self.mini_size[1] * 3, bd=-2)
            self.selected_cam_frame.grid(row=1, column=0, columnspan=3)
            self.selected_cam_frame.grid_remove()

            self.selected_cam_label = tk.Label(master=self.selected_cam_frame, bg='yellow', borderwidth=2)
            self.selected_cam_label.pack(fill=tk.BOTH)

    def update(self):
        for process_id, cam in self.cams:
            if self.current_output[process_id] is not None:
                image = Image.fromarray(self.current_output[process_id])
                image = ImageTk.PhotoImage(image.resize((self.mini_size[0], self.mini_size[1]), Image.ANTIALIAS))
                self.cam_labels[process_id].config(image=image)
                self.cam_labels[process_id].image = image

        if self.selected_cam is not None:
            if self.current_output[self.selected_cam] is not None:
                image = Image.fromarray(self.current_output[self.selected_cam])
                image = ImageTk.PhotoImage(
                    image.resize((self.mini_size[0] * 3 + 8, self.mini_size[1] * 3 + 8), Image.ANTIALIAS))
                self.selected_cam_label.config(image=image)
                self.selected_cam_label.image = image

        if self.alive_flag.is_set():
            this_frame = time.perf_counter()
            # print(f'FPS: {1 / (this_frame - self.last_frame)}')
            self.last_frame = this_frame
            self.window.after(30, self.update)
        else:
            self.window.quit()

    def select_window(self, clicked_cam):
        if self.selected_cam == clicked_cam:
            self.cam_labels[clicked_cam].config(bg='black')
            self.selected_cam = None
            self.selected_cam_frame.grid_remove()
        else:
            self.cam_labels[clicked_cam].config(bg='yellow')
            if self.selected_cam is not None:
                self.cam_labels[self.selected_cam].config(bg='black')
            self.selected_cam = clicked_cam
            self.cam_labels[clicked_cam].config(bg='yellow')
            self.selected_cam_frame.grid()


class GUIHandler(Process):
    def __init__(self, alive_flag, current_output, process_names):
        super(GUIHandler, self).__init__()
        self.current_output = current_output
        self.process_names = process_names
        self.alive_flag = alive_flag

    def run(self):
        Application(self.alive_flag, tk.Tk(), self.current_output, self.process_names)
