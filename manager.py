import time
import socket
import threading

working_server = 1 #backup
backupIP = ""

def PrimaryThread():
    global working_server
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    primaryIP = socket.gethostbyname(socket.gethostname())
    PORT = 50052
    s.connect((primaryIP, PORT))
    try:
        while True:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((primaryIP, PORT))
            if result == 0 and working_server == 1:  # primary open && backup working
                print("send to primary: run")
                s.send("run".encode())
                working_server = 0
            elif result == 1 and working_server == 0:  # primary crash
                working_server = 1
                
            time.sleep(1)
    except KeyboardInterrupt:
        print("keyboard interrupt...")
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        return

def BackupThread():
    '''
    global backupIP
    PORT = 50052
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect((backupIP, PORT))
    try:
        while True:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = sock.connect_ex((backupIP, PORT))
            
                
                
            time.sleep(1)
    except KeyboardInterrupt:
        print("keyboard interrupt...")
        s.shutdown(socket.SHUT_RDWR)
        s.close()
        return
    '''
    pass

if __name__ == '__main__':
    try:
        #backupIP = "192.168.220.128"
        #backupIP = input("IP:PORT for backup server: ")
        primary_thread = threading.Thread(target=PrimaryThread)
        primary_thread.start()
        backup_thread = threading.Thread(target=BackupThread)
        backup_thread.start()
        while(1):
            pass
    except KeyboardInterrupt:
        primary_thread.join()
        backup_thread.join()
        print("\nManager terminated")