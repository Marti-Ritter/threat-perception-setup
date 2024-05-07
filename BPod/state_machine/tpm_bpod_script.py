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


def softcode_handler(data):
    """
    Function to be called when a softcode is received

    :param data: Softcode from bpod
    :return: None
    """

    if data == experimental_variables["end_softcode"]:
        #code to handle end of trial
        pass
    elif data == experimental_variables["reward_softcode"]:
        #code to handle reward ("reward marker")
        pass


experimental_variables = {

    'start_delay': 0,
    'trial_timeout':0,
    'lick_timeout': 0,
    'reward_delay': 0,
    'reward_time': 0,
    'timeout_punish': 0,
    'fail_punish': 0,
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

import logging
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)
from pybpodapi.bpod_modules.bpod_modules import BpodModules

logger.debug('Calling constructor')
pod = Bpod('COM5')
logger.debug('Called constructor')
#pod.open()
print('Modules:', pod.modules)
for module in pod.modules:
    print(f'Module.name: {module.name}  - {module.serial_port}')

sma = build_state_machine(pod, **experimental_variables)
pod.softcode_handler_function = softcode_handler

pod.send_state_machine(sma)
pod.run_state_machine(sma)

pod.close()
