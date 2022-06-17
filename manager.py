from glob import glob
import time
import socket
import threading

working_server = 1 # primary:1 backup:-1
alive_server = [None, True, True]
sock = {}
mutex = [threading.Lock(), threading.Lock(), threading.Lock()] # mutex[0] is unused
primaryRestore = None
'''
def PrimaryThread(sID, sIP, sPORT):
    global working_server
    global sock
    global mutex
    global primaryRestore
    while True:
        try:
            sock[sID] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock[sID].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock[sID].connect((sIP, sPORT))
            print("[Manager +] Connect primary done.")
            time.sleep(0.1)
            sock[sID].send("PRIMARY".encode())
            time.sleep(0.1)
            if working_server == 1:
                sock[-sID].send("SyncSend".encode())
                working_server = 0
                mutex.acquire()
                sock[sID].send(primaryRestore.encode())  # forword data to primary   
                print("[Manager +] Restore to primary.")
        
            while working_server == 0:  # primary power-on
                primaryCOMM = sock[sID].recv(1024)
                if len(primaryCOMM) > 0:
                    primaryCOMM = primaryCOMM.decode()
                    op = primaryCOMM.split()[0]
                    if op == "SyncRecv":             # handle sync from primary's new data
                        msg = primaryCOMM
                        sock[-sID].send(msg.encode())  # forword data to backup
                        print("[Manager +] Sync to backup.")
                else:
                    raise ConnectionResetError

        except ConnectionResetError:
            print("[Manager -] Primary crash detected.")
            working_server = 1
            sock[sID].shutdown(socket.SHUT_RDWR)
            sock[sID].close()
                
        except KeyboardInterrupt:
            print("[Manager -] Keyboard interrupted.")
            sock[sID].shutdown(socket.SHUT_RDWR)
            sock[sID].close()
            return
        
        except ConnectionRefusedError: 
            # primary still crash, reconnect
            time.sleep(0.3)
        
        except Exception as e:
            print("[Manager -] PrimaryThread error: "+str(e))
            

def BackupThread(sID, sIP, sPORT):
    global sock
    global mutex
    global primaryRestore
    sock[sID] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock[sID].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock[sID].connect((sIP, sPORT))

    try:
        while True:
            backupCOMM = sock[sID].recv(1024)
            if len(backupCOMM) > 0:
                backupCOMM = backupCOMM.decode()
                op = backupCOMM.split()[0]
                
                if op == "SyncRecv":
                    primaryRestore = backupCOMM
                    print("[Manager +] Send restore signal.")
                    mutex.release()
                
    except KeyboardInterrupt:
        print("[Manager -] Keyboard interrupted.")
        sock[sID].shutdown(socket.SHUT_RDWR)
        sock[sID].close()
        
        return
    except Exception as e:
        print("[Manager -] BackupThread error: "+str(e))
'''

def serverThread(sID, sIP, sPORT):
    global alive_server
    global sock
    global mutex
    global primaryRestore
    while True:
        try:
            sock[sID] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock[sID].setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock[sID].connect((sIP, sPORT))
            print("[Manager +] Connect server", sID, "done.")
            time.sleep(0.1)
            if sID == 1:
                sock[sID].send("PRIMARY".encode())
                time.sleep(0.1)
            # if sID just relive
            if alive_server[sID] == False:
                sock[-sID].send("SyncSend".encode())
                alive_server[sID] = True
                #mutex[sID].acquire()
                sock[sID].send(primaryRestore.encode())  # forword data to primary    
                print(f"[Manager +] Restore to {sID} .")
        
            while True:
                command = sock[sID].recv(1024)
                if len(command) > 0:
                    command = command.decode()
                    op = command.split()[0]
                    if op == "SyncRecv":             # handle sync from primary's new data
                        primaryRestore = command
                        sock[-sID].send(primaryRestore.encode())  # forword data to backup
                        print("[Manager +] Sync to", -sID)

                else:
                    raise ConnectionResetError

        except ConnectionResetError:
            print("[Manager -] Server ",sID," crash detected.")
            alive_server[sID] = False
            sock[sID].shutdown(socket.SHUT_RDWR)
            sock[sID].close()
                
        except KeyboardInterrupt:
            print("[Manager -] Keyboard interrupted.")
            sock[sID].shutdown(socket.SHUT_RDWR)
            sock[sID].close()
            return
        
        except ConnectionRefusedError: 
            # primary still crash, reconnect
            time.sleep(0.3)
        
        except Exception as e:
            print("[Manager -] serverThread error: "+str(e))
            


if __name__ == '__main__':
    try:
        primaryIP = socket.gethostbyname(socket.gethostname())
        primaryPORT = 50052
        backupIP = input("IP for backup server: ")
        #backupIP = "192.168.220.128"
        backupPORT = 50052

        mutex[1].acquire()
        mutex[-1].acquire()
        primary_thread = threading.Thread(
            target=serverThread, daemon=True, args=(1, primaryIP, primaryPORT))
        primary_thread.start()

        backup_thread = threading.Thread(
           target=serverThread, daemon=True, args=(-1, backupIP, backupPORT))
        backup_thread.start()
        
        while True: 
            time.sleep(100)
    except KeyboardInterrupt:
        print("\n[Manager] Terminated")