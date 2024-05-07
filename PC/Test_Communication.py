import socket
import select

raspi_ip = '169.254.233.213'
username = 'root'
password = 'TPM'
port = 6666

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
client_socket.connect((raspi_ip, port))
client_socket.setblocking(False)

try:
    while 1:
        data = input("Enter Data :")
        client_socket.send(data.encode())
        print("Sending request")

        ready = select.select([client_socket], [], [], 3)
        if ready[0]:
            msgReceived = client_socket.recv(1024)
            print("At client: %s" % str(msgReceived.decode()))
            if msgReceived.decode() == 'shutdown':
                client_socket.close()
                quit()


except Exception as ex:
    print(ex)
