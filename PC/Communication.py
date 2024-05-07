import socket
import select
import threading
from queue import Queue

connection_settings = {
#    'raspi_ip': '192.168.178.47',
    'raspi_ip': '169.254.233.213',
    'port': 6666,
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
    client_socket.setblocking(False)
    return client_socket


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
