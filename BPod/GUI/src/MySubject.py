import tkinter as tk
from copy import copy
import sys
import os
import glob

from .MyVariables import MySettingGroup, MySetting, MyTrialSettings
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import enum
import json


class MySubjectType(enum.Enum):

    RAT = "Rat"
    MOUSE = "Mouse"

class MySubject:

    def __init__(self, id, name, subject_type):

        assert isinstance(subject_type, MySubjectType)
        self.subject_type = subject_type
        self.id = id
        self.name = name

    def get_display_name(self):

        return "{id} ({name})".format(id=self.id, name=self.name)

    def to_json(self):

        data = {
            "subject_type":self.subject_type.value,
            "id":self.id,
            "name":self.name
        }
        return json.dumps(data)

    def from_json(self):
        pass



class MySubjectManager:

    def __init__(self, subject_type, name):

        assert isinstance(subject_type,MySubjectType)
        self.subject_type  = subject_type
        self.name = name
        self.path = "./subjects/"+self.subject_type.value
        self.subjects = []

    def id_exists(self,id):

        for s in self.subjects:
            if s.id == id:
                return True

        return False
    def add_subject(self,subject):

        assert isinstance(subject,MySubject)
        assert subject.subject_type.value == self.subject_type.value
        self.subjects.append(subject)

    def delete_subject(self, subject):


        self.subjects.remove(subject)


    def get_subjects(self):

        return self.subjects

    def get_subject(self,i):
        return self.subjects[i]

    def save_subjects(self):

        for file in glob.glob(os.path.join(self.path,"*")):
            os.remove(file)

        for subject in self.subjects:
            file = os.path.join(self.path, "{id}_{n}.subject".format(id = subject.id, n = subject.name))
            os.makedirs(self.path,exist_ok=True)

            if not os.path.exists(file):
                mode = "x"
            else:
                mode = "w"

            with open(file, mode) as f:
                f.write(subject.to_json())

    def load_subjects(self):


        for subject_file in glob.glob(os.path.join(self.path,"*")):
            subject = MySubject(0,"",self.subject_type)
            with open(subject_file,"r") as f:
                subject_data = json.load(f)

            subject.id = subject_data["id"]
            subject.name = subject_data["name"]
            self.add_subject(subject)


