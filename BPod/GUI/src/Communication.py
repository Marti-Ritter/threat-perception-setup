"""
author: Marti Ritter

"""

import socket
import select
import threading
from queue import Queue

connection_settings = {
    'raspi_ip': '192.168.178.47',
#    'raspi_ip': '169.254.233.213',
    'port': 6666,
}

raspi_flags = {
    'connected': False,
    'screen_active': False,
}


# Stuff to make input non-blocking
# (adapted from https://stackoverflow.com/questions/2408560/python-nonblocking-console-input, Marco)
class KeyboardThread(threading.Thread):
    def __init__(self, input_cbk, input_queue, name='keyboard-input-thread'):
        self.input_cbk = input_cbk
        self.input_queue = input_queue
        super(KeyboardThread, self).__init__(name=name)
        self.daemon = True
        self._is_running = True
        self.start()

    def stop(self):
        self._is_running = False

    def run(self):
        while self._is_running:
            self.input_cbk(input(), self.input_queue)


def my_callback(inp, input_queue):
    input_queue.put(inp)


# to connect to raspi
def create_connection(ip, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    client_socket.connect((ip, port))
    raspi_flags['connected'] = True
    client_socket.setblocking(False)
    return client_socket


# to start screen
def start_screen(connection):
    connection.send('1'.encode())


# to close screen
def close_screen(connection):
    connection.send('4'.encode())


# to get a setting
def get_option(connection, key=None):
    if key:  # works with a specific key
        connection.send(f'get_option {key}'.encode())
    else:   # or none, the raspi then sends the full settings dict
        connection.send(f'get_option'.encode())


# to set a setting
def set_option(connection, key_value_pair):
    # for now the communication is string-based, later will be using pickle
    # this means that boolean keys have to be encoded into True=anything and False=''
    # since any string which is not empty will be cast as boolean True
    connection.send(f'set_option {key_value_pair[0]} {key_value_pair[1]}'.encode())


# to start a trial
def start_trial(connection):
    connection.send('2'.encode)


# to end a trial
def end_trial(connection):
    connection.send('3'.encode)


# to set the disk state
def set_disk(connection, state):
    # states are between 0 and 3
    connection.send(f'set_disk {state}'.encode)


# to quit the program on the raspberry pi, should'nt use this
def end(connection):
    connection.send('end'.encode)


# to quit the program on the raspberry pi, and shut it down
def shutdown(connection, state):
    connection.send('shutdown'.encode)


if __name__ == '__main__':
    try:
        client_socket = create_connection(connection_settings['raspi_ip'], connection_settings['port'])
        current_orders = Queue()
        user_input_thread = KeyboardThread(my_callback, current_orders)

        # Has to be in mainloop
        while True:
            # outbound communication
            while not current_orders.empty():
                data = current_orders.get()
                client_socket.send(data.encode())

            # inbound communication
            ready_to_read, ready_to_write, in_error = select.select([client_socket], [], [], 0.5)
            if len(ready_to_read) > 0:
                msgReceived = client_socket.recv(1024)
                print(f'At client: {str(msgReceived.decode())}')
                if msgReceived.decode() == 'shutdown':
                    user_input_thread.stop()
                    user_input_thread.join()
                    client_socket.close()
                    quit()

    except Exception as ex:
        print(ex)
