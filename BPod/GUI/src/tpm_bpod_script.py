import signal
import sys
import time

from pybpodapi.protocol import Bpod, StateMachine


def build_state_machine(pod, **kwargs):
    """
    builds state machine from experimental variables passed as kwargs
    :param pod: Bpod object
    :param kwargs: experimental varialbles
    :return: state machine
    """
    sma = StateMachine(pod)

    """Time up delays"""
    start_delay = kwargs['start_delay']
    trial_timeout = kwargs['trial_timeout']
    lick_timeout = kwargs['lick_timeout']
    reward_delay = kwargs['reward_delay']
    reward_time = kwargs['reward_time']
    timeout_punish = kwargs['timeout_punish']
    fail_punish = kwargs['fail_punish']

    """
    softcodes (bpod -- computer) and bytes (bpod -- serial) to be send for some transitions 
    softcode/serial do not have to be identical
    """
    reward_softcode = kwargs['reward_softcode']
    reward_byte = kwargs['reward_byte']
    end_softcode = kwargs['end_softcode']
    end_byte = kwargs['end_byte']
    start_byte = kwargs['start_byte']
    pos_byte = kwargs['pos_byte']

    """
    output channel and value to dispense reward
    """
    reward_output = kwargs['reward_output']
    reward_value = kwargs['reward_value']

    """
    Bpod event to be interpreted as lick
    """
    lick_event = kwargs['lick_event']
    serial = kwargs['serial']

    """
    Condition to interpret positional trigger from raspberry pi
    """
    pos_trigger = Bpod.Events.Condition1,
    pos_trigger = pos_trigger[0]

    sma.set_condition(condition_number=1, condition_channel='Serial1', channel_value=pos_byte)

    """
    Add states to SMA
    """

    """Start"""
    sma.add_state(
        state_name='S0',
        state_timer=start_delay,
        state_change_conditions={Bpod.Events.Tup: 'S1'},
        output_actions=[(serial, start_byte)]
    )

    """Trial"""
    sma.add_state(
        state_name='S1',
        state_timer=trial_timeout,
        state_change_conditions={pos_trigger: 'S2',Bpod.Events.Tup: 'S5'},
        output_actions=[]
    )

    """Success"""
    sma.add_state(
        state_name='S2',
        state_timer=lick_timeout,
        state_change_conditions={Bpod.Events.Tup: 'S6', lick_event: 'S3'},
        output_actions=[]
    )

    sma.add_state(
        state_name='S3',
        state_timer=reward_delay,
        state_change_conditions={Bpod.Events.Tup: 'S4'},
        output_actions=[(serial, reward_byte), (Bpod.OutputChannels.SoftCode, reward_softcode),
                        (reward_output, reward_value)]
    )

    sma.add_state(
        state_name='S4',
        state_timer=reward_time,
        state_change_conditions={Bpod.Events.Tup: 'exit'},
        output_actions=[(serial, end_byte), (Bpod.OutputChannels.SoftCode, end_softcode)]
    )

    """Trial Timeout"""
    sma.add_state(
        state_name='S5',
        state_timer=timeout_punish,
        state_change_conditions={Bpod.Events.Tup: 'exit'},
        output_actions=[(serial, end_byte), (Bpod.OutputChannels.SoftCode, end_softcode)]
    )

    """Lick Timeout"""

    sma.add_state(
        state_name='S6',
        state_timer=fail_punish,
        state_change_conditions={Bpod.Events.Tup: 'exit'},
        output_actions=[(serial, end_byte), (Bpod.OutputChannels.SoftCode, end_softcode)]
    )

    return sma



class SoftcodeHandler:

    def __init__(self,experimental_variables):

        self.experimental_variables = experimental_variables

    def handle(self,data):

        """
        Function to be called when a softcode is received

        :param data: Softcode from bpod
        :return: None
        """

        if data == self.experimental_variables["end_softcode"]:
            #code to handle end of trial;
            pass
        elif data == self.experimental_variables["reward_softcode"]:
            #code to handle reward ("reward marker"); is called when the mouse licked
            pass


def run_trial(pod,experimental_variables,flags):

    def terminate_handler(signum, stackframe):

        close(pod,flags)
        sys.exit(0)

    signal.signal(signal.SIGTERM, terminate_handler)

    for k,v in experimental_variables_defaults.items():
        if not k in experimental_variables.keys():
            experimental_variables[k] = v

    sma = build_state_machine(pod, **experimental_variables)
    soft = SoftcodeHandler(experimental_variables)

    pod.softcode_handler_function = soft.handle
    pod.send_state_machine(sma)

    flags["pod_ready"].set()

    flags["pi_ready"].wait()
    flags["run"].wait()

    pod.run_state_machine(sma)

    flags["pod_ready"].clear()


def run_single_trial(experimental_variables,flags):

    pod = open(flags)

    run_trial(pod,experimental_variables,flags)

    close(pod,flags)

def open(flags):
    pod = Bpod()
    pod.open()

    return pod

def close(pod,flags):

    flags["pod_ready"].clear()
    flags["run"].clear()

    pod.close()

def run_multiple_trials(experimental_variables,flags):

    pod = open(flags)

    n = experimental_variables["repeats"]
    for i in range(n):
        run_trial(pod,experimental_variables,flags)

    close(pod,flags)




experimental_variables_defaults = {

    'repeats':5,
    'start_delay': 1,
    'trial_timeout':1,
    'lick_timeout': 1,
    'reward_delay': 1,
    'reward_time': 1,
    'timeout_punish': 1,
    'fail_punish': 1,
    'reward_softcode': int.from_bytes(b'R', 'big'),
    'reward_byte': int.from_bytes(b'R', 'big'),
    'end_softcode': int.from_bytes(b'E', 'big'),
    'end_byte': int.from_bytes(b'E', 'big'),
    'start_byte': int.from_bytes(b'S', 'big'),
    'pos_byte': int.from_bytes(b'POS', 'big'),
    'reward_output': Bpod.OutputChannels.BNC1,
    'reward_value': 255,
    'lick_event': Bpod.Events.BNC2High,
    'serial': Bpod.OutputChannels.Serial1

}

if __name__ == "__main__":
    run_multiple_trials(experimental_variables)


