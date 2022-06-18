from glob import glob
import time
import socket
import threading


working_server = 1 # primary:1 backup:-1
alive_server = [None, True, True]
sock = {}
mutex = [threading.Lock(), threading.Lock(), threading.Lock()] # mutex[0] is unused
primaryRestore = ""
ACK_res = -1

def serverThread(sID, sIP, sPORT):
    global alive_server
    global sock
    global mutex, ACK_res
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
            if alive_server[sID] == False:  # if sID just relive
                alive_server[sID] = True

                ############# first restore #############
                sock[-sID].send("SyncSend".encode())
                command = sock[sID].recv(4096)
                if len(command) > 0:
                    command = command.decode()
                    op = command.split()[0]
                    if op == "ACK":
                        ACK_res = 1
                        print(f"[Manager +] Restore to {sID} : ACK.")
                        sock[-sID].send("restoreACK".encode())
                    elif op == "NAK":
                        ACK_res = 0
                        print(f"[Manager -] Restore to {sID} : NAK.")
                        sock[-sID].send("restoreNAK".encode())
                    else:
                        ACK_res = 0
                        print(f"[Manager -] Restore to {sID} : response {op} not defined.")
                        sock[-sID].send("restoreNAK".encode())
                else:
                    print("[Manager -] raise restore ConnectionResetError")
                    raise ConnectionResetError
                
                ############# second restore #############
                sock[sID].send("SyncSend".encode())
                if mutex[sID].locked():
                    mutex[sID].release()
                    
            while True:
                command = sock[sID].recv(4096)
                if len(command) > 0:
                    command = command.decode()
                    op = command.split()[0]
                    if op == "SyncRecv":             # handle sync from primary's new data
                        primaryRestore = command
                        ACK_res = -1
                        print("[Manager +] Sync to", -sID,". Waiting for response...")
                        try:
                            sock[-sID].send(primaryRestore.encode())  # forword data to backup
                        except OSError:
                            print("[Manager -] Server", -sID, "crashed, so SyncRecv blocked.")
                            sock[sID].send("NAK".encode())
                            continue
                        if mutex[-sID].acquire(timeout=5):
                            if ACK_res == 1:
                                print("[Manager +] ACK from server", -sID)
                                sock[sID].send("ACK".encode())
                            elif ACK_res == 0:
                                print("[Manager +] NAK from server", -sID)
                                sock[sID].send("NAK".encode())
                            else:
                                print("[Manager -] ACK_response:", ACK_res, "undefined.")
                                sock[sID].send("NAK".encode())
                        else:
                            print("[Manager -] ACK_response from server", -sID, "timeout.")
                            sock[sID].send("NAK".encode())

                    elif op == "ACK" or op == "NAK":
                        ACK_res = 1 if op == "ACK" else 0
                        try:
                            mutex[sID].release()
                        except:
                            pass
                else:
                    print("[Manager -] raise ConnectionResetError")
                    raise ConnectionResetError

        except ConnectionResetError:
            print("[Manager -] Server", sID, "crash detected.")
            alive_server[sID] = False
            sock[sID].shutdown(socket.SHUT_RDWR)
            sock[sID].close()
                
        except KeyboardInterrupt:
            print("[Manager -] Keyboard interrupted.")
            sock[sID].shutdown(socket.SHUT_RDWR)
            sock[sID].close()
            return
        
        except ConnectionRefusedError: 
            # server still crash, reconnect
            print("[Manager -] Server", sID, "crash detected.")
            alive_server[sID] = False
            time.sleep(0.1)
        except TimeoutError: 
            # server still crash, reconnect
            print("[Manager -] Server", sID, "crash detected.")
            alive_server[sID] = False
            time.sleep(0.1)
        
        except Exception as e:
            print("[Manager -] serverThread error: "+str(e))
            


if __name__ == '__main__':
    try:
        primaryIP = socket.gethostbyname(socket.gethostname())
        primaryPORT = 50052
        #backupIP = input("IP for backup server: ")
        backupIP = "192.168.220.128"
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