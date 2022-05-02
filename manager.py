import time
import socket
import threading

working_server = 0 # primary
backupIP = ""
backupSOCK = None
primarySOCK = None

def PrimaryThread():
    global working_server
    global backupSOCK
    global primarySOCK
    while True:
        try:
            primarySOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            primarySOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            primaryIP = socket.gethostbyname(socket.gethostname())
            primaryPORT = 50052
            primarySOCK.connect((primaryIP, primaryPORT))
            time.sleep(0.1)
            primarySOCK.send("PRIMARY".encode())
            time.sleep(0.1)
            if working_server == 1:
                backupSOCK.send("RESTORE".encode())
                working_server == 0
        
            while working_server == 0:  # primary power-on
                primaryCOMM = primarySOCK.recv(1024)
                if len(primaryCOMM) > 0:
                    primaryCOMM = primaryCOMM.decode()
                    print("receive from primary : "+str(primaryCOMM))
                    op = primaryCOMM.split()[0]

                    if op == "SYNC":             # handle sync from primary's new data
                        msg = primaryCOMM
                        backupSOCK.send(msg.encode())  # forword data to backup
                        print("sync manager->backup done")

        except ConnectionResetError:
            print("primary crash detected")
            working_server = 1
            #backupSOCK.send("primary".encode())
            primarySOCK.shutdown(socket.SHUT_RDWR)
            primarySOCK.close()
                
        except KeyboardInterrupt:
            print("keyboard interrupt...")
            primarySOCK.shutdown(socket.SHUT_RDWR)
            primarySOCK.close()
            return
        
        except ConnectionRefusedError: 
            # primary still crash, reconnect
            time.sleep(2)
            

def BackupThread():
    global backupIP
    global backupSOCK
    global primarySOCK
    backupSOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    backupSOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    backupPORT = 50052
    backupSOCK.connect((backupIP,backupPORT))

    try:
        while True:
            backupCOMM = backupSOCK.recv(1024)
            if len(backupCOMM) > 0:
                backupCOMM = backupCOMM.decode()
                print("receive from backup : "+str(backupCOMM))
                op = backupCOMM.split()[0]
                
                if op == "RESTORE":
                    msg = backupCOMM
                    print("send restore..")
                    primarySOCK.send(msg.encode())  # forword data to primary                    
                    print("restore manager->primary done")
                
    except KeyboardInterrupt:
        print("keyboard interrupt...")
        backupSOCK.shutdown(socket.SHUT_RDWR)
        backupSOCK.close()
        
        return
    except Exception as e:
        print("backup thread error: "+str(e))

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