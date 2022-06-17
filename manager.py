from glob import glob
import time
import socket
import threading

working_server = 0 # primary
backupIP = ""
sock = {}
sock["backup"] = None
sock["primary"] = None
mutex = threading.Lock()
primaryRestore = None

def PrimaryThread():
    global working_server
    global sock
    global mutex
    global primaryRestore
    while True:
        try:
            sock["primary"] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock["primary"].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            primaryIP = socket.gethostbyname(socket.gethostname())
            primaryPORT = 50052
            sock["primary"].connect((primaryIP, primaryPORT))
            print("[Manager +] Connect primary done.")
            time.sleep(0.1)
            sock["primary"].send("PRIMARY".encode())
            time.sleep(0.1)
            if working_server == 1:
                sock["backup"].send("SyncSend".encode())
                working_server = 0
                mutex.acquire()
                sock["primary"].send(primaryRestore.encode())  # forword data to primary                    
                print("[Manager +] Restore to primary.")
        
            while working_server == 0:  # primary power-on
                primaryCOMM = sock["primary"].recv(1024)
                if len(primaryCOMM) > 0:
                    primaryCOMM = primaryCOMM.decode()
                    op = primaryCOMM.split()[0]
                    if op == "SyncRecv":             # handle sync from primary's new data
                        msg = primaryCOMM
                        sock["backup"].send(msg.encode())  # forword data to backup
                        print("[Manager +] Sync to backup.")
                else:
                    raise ConnectionResetError

        except ConnectionResetError:
            print("[Manager -] Primary crash detected.")
            working_server = 1
            sock["primary"].shutdown(socket.SHUT_RDWR)
            sock["primary"].close()
                
        except KeyboardInterrupt:
            print("[Manager -] Keyboard interrupted.")
            sock["primary"].shutdown(socket.SHUT_RDWR)
            sock["primary"].close()
            return
        
        except ConnectionRefusedError: 
            # primary still crash, reconnect
            time.sleep(0.3)
        
        except Exception as e:
            print("[Manager -] PrimaryThread error: "+str(e))
            

def BackupThread():
    global backupIP
    global sock
    global mutex
    global primaryRestore
    sock["backup"] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock["backup"].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    backupPORT = 50052
    sock["backup"].connect((backupIP,backupPORT))

    try:
        while True:
            backupCOMM = sock["backup"].recv(1024)
            if len(backupCOMM) > 0:
                backupCOMM = backupCOMM.decode()
                op = backupCOMM.split()[0]
                
                if op == "SyncRecv":
                    primaryRestore = backupCOMM
                    print("[Manager +] Send restore signal.")
                    mutex.release()
                
    except KeyboardInterrupt:
        print("[Manager -] Keyboard interrupted.")
        sock["backup"].shutdown(socket.SHUT_RDWR)
        sock["backup"].close()
        
        return
    except Exception as e:
        print("[Manager -] BackupThread error: "+str(e))

if __name__ == '__main__':
    try:
        #backupIP = input("IP for backup server: ")
        backupIP = "192.168.220.128"
        mutex.acquire()
        primary_thread = threading.Thread(target=PrimaryThread, daemon=True)
        primary_thread.start()

        backup_thread = threading.Thread(target=BackupThread, daemon=True)
        backup_thread.start()
        
        while True: 
            time.sleep(100)
    except KeyboardInterrupt:
        print("\n[Manager] Terminated")