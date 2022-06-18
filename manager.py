import time
import socket
import threading


alive_server = [None, True, True]
sock = {}
mutex = [threading.Lock(), threading.Lock(), threading.Lock()] # mutex[0] is unused
primaryRestore = ""
ACK_res = -1

def printc(str, color = 'white'):
    if color == 'red':
        print('\033[1;31m' + str + '\033[0;37m')
    elif color == 'green':
        print('\033[1;32m' + str + '\033[0;37m')
    elif color == 'yellow':
        print('\033[1;33m' + str + '\033[0;37m')
    else:
        print('\033[0;37m' + str + '\033[0;37m')

def testThread(sID,sIP,sPORT):
    global alive_server, sock
    while True:
        try:
            testsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            testsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            testsock.settimeout(5)
            testsock.connect((sIP, sPORT+1))
            print(f"testThread {sID} connected.")
            while True:
                command = testsock.recv(4096)
                if len(command) > 0:
                    print(f"Recieve from {sID}: {command.decode()}")
                    testsock.send("OK".encode())
                else:
                    print(f"TestThread error: server {sID} len <= 0")
                    alive_server[sID] = False
                    try:
                        sock[sID].shutdown(socket.SHUT_RDWR)
                        sock[sID].close()
                    except:
                        pass
                    break
        except (ConnectionRefusedError, ConnectionResetError):
            pass

        except socket.timeout:
            print(f"TestThread error: server {sID} TIMEOUT")
            alive_server[sID] = False
            try:
                sock[sID].shutdown(socket.SHUT_RDWR)
                sock[sID].close()
            except:
                pass


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
            printc(f"[Manager +] Connect server {sID} done.", 'green')
            time.sleep(0.5)
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
                        printc(f"[Manager +] Restore to {sID} : ACK.", 'green')
                        sock[-sID].send("restoreACK".encode())
                    elif op == "NAK":
                        ACK_res = 0
                        printc(f"[Manager -] Restore to {sID} : NAK.", 'red')
                        sock[-sID].send("restoreNAK".encode())
                    else:
                        ACK_res = 0
                        printc(f"[Manager -] Restore to {sID} : response {op} not defined.", 'red')
                        sock[-sID].send("restoreNAK".encode())
                else:
                    printc("[Manager -] raise restore ConnectionResetError", 'red')
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
                    if op == "SyncRecv":             # redirect Sync data
                        primaryRestore = command
                        ACK_res = -1
                        printc(f"[Manager +] Sync to {-sID}. Waiting for response...", 'green')
                        try:
                            sock[-sID].send(primaryRestore.encode())  # forword data to another server
                        except OSError:
                            printc(f"[Manager -] Server {-sID} crashed, so SyncRecv blocked.", 'yellow')
                            sock[sID].send("NAK".encode())
                            continue
                        if mutex[-sID].acquire(timeout=5):
                            if ACK_res == 1:
                                printc(f"[Manager +] ACK from server {-sID}.", 'green')
                                sock[sID].send("ACK".encode())
                            elif ACK_res == 0:
                                printc(f"[Manager +] NAK from server {-sID}.", 'yellow')
                                sock[sID].send("NAK".encode())
                            else:
                                printc(f"[Manager -] ACK_response:{ACK_res} undefined.", 'red')
                                sock[sID].send("NAK".encode())
                        else:
                            printc(f"[Manager -] ACK_response from server {-sID} TIMEOUT.", 'yellow')
                            sock[sID].send("NAK".encode())

                    elif op == "ACK" or op == "NAK":
                        ACK_res = 1 if op == "ACK" else 0
                        try:
                            mutex[sID].release()
                        except:
                            pass
                else:
                    printc("[Manager -] raise ConnectionResetError.", 'red')
                    raise ConnectionResetError

        except ConnectionResetError:
            printc(f"[Manager -] Server {sID} crash detected.", 'red')
            alive_server[sID] = False
            try:
                sock[sID].shutdown(socket.SHUT_RDWR)
                sock[sID].close()
            except:
                pass
                
        except KeyboardInterrupt:
            print("[Manager] Keyboard interrupted.")
            sock[sID].shutdown(socket.SHUT_RDWR)
            sock[sID].close()
            return
        
        except ConnectionRefusedError: 
            # server still crash, reconnect
            printc(f"[Manager -] Server {sID} crash detected.(REFUSED)", 'red')
            alive_server[sID] = False
            time.sleep(0.1)
        
        except TimeoutError: 
            # server still crash, reconnect
            printc(f"[Manager -] Server {sID} crash detected.(TIMEOUT)", 'red')
            alive_server[sID] = False
            try:
                sock[sID].shutdown(socket.SHUT_RDWR)
                sock[sID].close()
            except:
                pass
            time.sleep(0.1)
        except OSError:
            printc(f"[Manager -] Server {sID} crash detected.(OSError)", 'red')
            alive_server[sID] = False
            time.sleep(0.1)

        '''
        except Exception as e:
            printc("[Manager -] serverThread error: "+str(e), 'red')
            '''


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
        
        test_primary = threading.Thread(
           target=testThread, daemon=True, args=(1, primaryIP, primaryPORT))
        test_primary.start()

        test_backup = threading.Thread(
           target=testThread, daemon=True, args=(-1, backupIP, backupPORT))
        test_backup.start()

        while True: 
            time.sleep(100)
    except KeyboardInterrupt:
        print("\n[Manager] Terminated")