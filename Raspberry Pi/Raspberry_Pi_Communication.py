# built-ins
import socket
import json
import multiprocessing
import select
import time
import os
from subprocess import call
import serial
import struct

# project modules
from Raspberry_Pi_Utility import Instructions
import Raspberry_Pi_Setup_Control

with open('./Raspberry_Pi_settings.json', 'r') as read_file:
    settings = json.load(read_file)

# processes
record_process = None
screen_pipe, at_screen = multiprocessing.Pipe()


def init_screen(*args):
    global record_process
    if not record_process:
        record_process = multiprocessing.Process(target=Raspberry_Pi_Setup_Control.experiment_loop,
                                                 args=(at_screen, settings))
        record_process.daemon = True
        record_process.start()


def init_screen_bpod(*args):
    global record_process
    if not record_process:
        record_process = multiprocessing.Process(target=Raspberry_Pi_Setup_Control.mouse_pairing_loop_new,
                                                 args=(at_screen, settings))
        record_process.daemon = True
        record_process.start()


def start_trial(*args):
    if record_process:
        screen_pipe.send((Instructions.Start_Trial, True))


def start_trial_no_recording(*args):
    if record_process:
        screen_pipe.send((Instructions.Start_Trial, False))


def set_disk(disk_state, *args):
    if record_process:
        screen_pipe.send((Instructions.Set_Disk, int(disk_state)))


def set_disk0():
    if record_process:
        screen_pipe.send((Instructions.Set_Disk, 0))


def set_disk1():
    if record_process:
        screen_pipe.send((Instructions.Set_Disk, 1))


def set_disk2():
    if record_process:
        screen_pipe.send((Instructions.Set_Disk, 2))


def set_disk3():
    if record_process:
        screen_pipe.send((Instructions.Set_Disk, 3))


def end_trial(*args):
    if record_process:
        screen_pipe.send((Instructions.End_Trial,))


def init_pairing(*args):
    global record_process
    if not record_process:
        record_process = multiprocessing.Process(target=Raspberry_Pi_Setup_Control.mouse_pairing_loop,
                                                 args=(at_screen, settings))
        record_process.daemon = True
        record_process.start()


def shutdown_screen(*args):
    global record_process
    if record_process:
        screen_pipe.send((Instructions.Stop_Experiment,))
        print('recorder told to stop')
        record_process.join()
        record_process = None


def get_option(key=None, *args):
    if key:
        try:
            conn.send('{}: {}'.format(key, settings[key]).encode())
        except KeyError:
            conn.send("Unknown setting requested.".encode())
    else:
        conn.send(str(settings).encode())


def set_option(key, value, *args):
    try:
        settings[key] = type(settings[key])(value)
    except ValueError as error:
        conn.send('ValueError occurred. The provided value didnt type-match the existing value.'.encode())
        return
    with open('./Raspberry_Pi_settings.json', 'w') as write_file:
        json.dump(settings, write_file)
    conn.send('{}: {}'.format(key, settings[key]).encode())


def end(with_poweroff=False, *args):
    if record_process:
        screen_pipe.send((Instructions.Stop_Experiment,))
        record_process.join()
    if with_poweroff:
        call("sudo shutdown --poweroff now", shell=True)
    else:
        quit()


def shutdown(*args):
    end(with_poweroff=True)


valid_operations = {'end': end,
                    'shutdown': shutdown,
                    'get_option': get_option,
                    'set_option': set_option,
                    'init_screen': init_screen,
                    '1': start_trial,
                    'set_disk': set_disk,
                    '2': end_trial,
                    'shutdown_screen': shutdown_screen,
                    'pairing': init_pairing,
                    'init_screen_bpod': init_screen_bpod,
                    }

byte_operations = {1: start_trial,
                   10: start_trial_no_recording,
                   2: end_trial,
                   30: set_disk0,
                   31: set_disk1,
                   32: set_disk2,
                   33: set_disk3,
                   4: init_screen_bpod,
                   5: shutdown_screen
                   }

if __name__ == '__main__':
    try:
        os.nice(-20)
    except AttributeError:
        # not available on Windows
        pass

    # dir_path = os.path.dirname(os.path.realpath(__file__))
    # print(dir_path)

    # Create a Server Socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('', 6666))
    server_socket.listen(1)

    # Create a data-transfer Socket
    data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    data_socket.bind(('', 40000))
    data_socket.listen(1)

    # Create a Matlab-communication Socket
    matlab_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    matlab_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    matlab_socket.bind(('', 50000))
    matlab_socket.listen(1)

    # Create a UART Serial connection for Bpod
    firmwareVersion = 1
    moduleName = "RaspbPi"
    ser = serial.Serial("/dev/ttyS0", 1312500)

    control_mode = None

    while True:
        print("Raspberry Pi listening on socket 6666 and on serial.")
        while True:
            ready_to_read, _, _ = select.select([server_socket], [], [], 0)
            if len(ready_to_read) > 0:
                conn, client = server_socket.accept()
                control_mode = 'PC'
                print(f'PC control activated: {conn}, {client}')
                break
            bytesAvailable = ser.in_waiting
            if bytesAvailable > 0:
                control_mode = 'Bpod'
                print('Bpod control activated.')
                break

        # Receive data from client and decide which function to call
        while True:
            if control_mode == 'PC':
                # PC communications
                try:    # check if select fails
                    ready_to_read, ready_to_write, _ = select.select([conn], [conn], [], 1)
                    if len(ready_to_read) > 0:
                        dataFromClient = conn.recv(256)
                        try:
                            message = dataFromClient.decode().split(' ')
                            if len(message) > 1:
                                valid_operations[message[0]](*message[1:])
                            else:
                                if message[0] in ['end', 'shutdown']:
                                    conn.send("shutdown".encode())
                                    server_socket.close()
                                valid_operations[message[0]]()
                        except KeyError as error:
                            conn.send("KeyError occurred. Function invalid.".encode())
                        except TypeError as error:
                            conn.send("TypeError occurred. Probably wrong count or type of argument.".encode())
                except select.error as error:
                    conn.close()
                    print(f'Select Error: {error}')
                    control_mode = None
                    break
                except socket.error as error:
                    conn.close()
                    print(f'Socket Error: {error}')
                    control_mode = None
                    break

            if control_mode == 'Bpod':
                # BPod communications
                bytesAvailable = ser.in_waiting
                if bytesAvailable > 0:
                    inByte = ser.read()
                    unpackedByte = struct.unpack('B', inByte)
                    print(f'{inByte} = {unpackedByte[0]}')
                    if unpackedByte[0] == 254:
                        message_string = ''
                        next_letter = ''
                        while next_letter != '|':
                            message_string += next_letter
                            next_letter = struct.unpack('s', ser.read())[0].decode()
                        message = message_string.split(' ')
                        if len(message) > 1:
                            valid_operations[message[0]](*message[1:])
                        else:
                            valid_operations[message[0]]()
                    elif unpackedByte[0] == 255:
                        # This code returns a self-description to the state machine.
                        Msg = struct.pack('B', 65)  # Acknowledgement
                        Msg += struct.pack('I', firmwareVersion)  # Firmware version as 32-bit unsigned int
                        Msg += struct.pack('B', len(moduleName))  # Length of module name
                        Msg += struct.pack(str(len(moduleName)) + 's', moduleName.encode('utf-8'))  # Module name
                        Msg += struct.pack('B', 0)  # 0 to indicate no more self description to follow
                        ser.write(Msg)
                    else:
                        try:
                            print(byte_operations[unpackedByte[0]])
                            byte_operations[unpackedByte[0]]()
                        except KeyError as error:
                            print("KeyError occurred. Function invalid.")
                    ser.flush()

                # Backup check for pc control, in case the Bpod dies
                ready_to_read, _, _ = select.select([server_socket], [], [], 0)
                if len(ready_to_read) > 0:
                    conn, client = server_socket.accept()
                    control_mode = 'PC'
                    print(f'PC override activated: {conn}, {client}')

            # internal communications
            if screen_pipe.poll():
                message = screen_pipe.recv()
                print(message)
                command = message[0]
                arguments = message[1:]
                if command is Instructions.Ready:
                    print('screen is ready')
                elif command is Instructions.Sending_Records:
                    received_dict = arguments[0]
                    received_json = json.dumps(received_dict)
                    print('RECEIVED ' + str(len(received_dict)) + ' LINES.')
                    if control_mode == 'PC':
                        conn.send(received_json.encode())
                    elif control_mode == 'Bpod':
                        matlab, _ = data_socket.accept()   # Bpod is too dumb for this
                        matlab.send(received_json.encode('utf-8'))
                elif command is Instructions.Trial_Aborted:
                    print('trial aborted')
                    if control_mode == 'PC':
                        conn.send('2'.encode())
                    elif control_mode == 'Bpod':
                        ser.write(struct.pack('B', 2))
                elif command is Instructions.Tube_Reached:
                    print('tube reached')
                    if control_mode == 'PC':
                        conn.send('1'.encode())
                    elif control_mode == 'Bpod':
                        ser.write(struct.pack('B', 1))
                elif command is Instructions.Tube_Reset:
                    print('tube reset')
                    if control_mode == 'PC':
                        conn.send('0'.encode())
                    elif control_mode == 'Bpod':
                        matlab_conn, _ = matlab_socket.accept()   # Bpod is too dumb for this
                        matlab_conn.send(b'0')
                else:
                    raise ValueError(f'Unknown message received: {message}')
