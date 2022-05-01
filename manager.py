import time
import socket
import threading
working_server = 1 #backup
backupIP = ""
backupSOCK = None

def PrimaryThread():
    global working_server
    global backupSOCK

    primarySOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    primarySOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    primaryIP = socket.gethostbyname(socket.gethostname())
    primaryPORT = 50052
    primarySOCK.connect((primaryIP, primaryPORT))
    
    try:
        while True:
            
            '''     # detect servers are alive?
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((primaryIP, primaryPORT))
            if result == 0 and working_server == 1:  # primary open && backup working
                print("send to primary: run")
                primarySOCK.send("run".encode())
                working_server = 0
            elif result == 1 and working_server == 0:  # primary crash
                working_server = 1
            
            '''
            try:
                primaryCOMM = primarySOCK.recv(1024)
                primaryCOMM = primaryCOMM.decode()
                print("receive from primary:"+str(primaryCOMM))
                varname = primaryCOMM.split()[0]

                if varname == "Voters":             # handle primary's new Voter 
                    msg = primaryCOMM
                    print("manager->backup : "+msg)
                    backupSOCK.send(msg.encode())  # forword Voter to backup
                    print("send new voter done")
                
            except BlockingIOError:
                time.sleep(3)
    except KeyboardInterrupt:
        print("keyboard interrupt...")
        primarySOCK.shutdown(socket.SHUT_RDWR)
        primarySOCK.close()
        
        return

def BackupThread():
    global backupIP
    global backupSOCK
    backupSOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    backupSOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    backupPORT = 50052
    backupSOCK.connect((backupIP,backupPORT))

    try:
        while True:
            time.sleep(100)
            '''
            try:
                backupCOMM = backupSOCK.recv(1024)
                backupCOMM = backupCOMM.decode()
                print("receive from backup:"+str(backupCOMM))
                varname = backupCOMM.split()[0]
                
                if varname == "???":
                    # restore data to primary
                    pass
                
            except BlockingIOError:
                time.sleep(3)
                '''
    except KeyboardInterrupt:
        print("keyboard interrupt...")
        backupSOCK.shutdown(socket.SHUT_RDWR)
        backupSOCK.close()
        
        return


if __name__ == '__main__':
    try:
        backupIP = "192.168.220.128"
        #backupIP = "192.168.181.137"
        #backupIP = input("IP:PORT for backup server: ")
        primary_thread = threading.Thread(target=PrimaryThread, daemon=True)
        primary_thread.start()

        backup_thread = threading.Thread(target=BackupThread, daemon=True)
        backup_thread.start()
        
        while True: 
            time.sleep(100)
    except KeyboardInterrupt:
        print("\nManager terminated")