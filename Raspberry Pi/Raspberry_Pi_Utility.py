from enum import Enum, auto


class Instructions(Enum):
    Ready = auto()
    Start_Trial = auto()
    Set_Disk = auto()
    Tube_Reached = auto()
    Trial_Aborted = auto()
    Tube_Reset = auto()
    End_Trial = auto()
    Sending_Records = auto()
    Stop_Experiment = auto()


class Phases(Enum):
    Trial = auto()
    Reward = auto()
    Inter_Trial = auto()
