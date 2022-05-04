import ast
import logging
import os
import sys
import threading
import tkinter as tk
from collections import deque
from concurrent import futures
from datetime import datetime, timedelta, timezone
from secrets import choice
from tkinter import ttk
from tokenize import group

import socket
import time


import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from nacl.public import Box, PrivateKey
from nacl.signing import VerifyKey
from nacl.encoding import Base64Encoder

sys.path.append('proto')
import proto.vote_pb2 as vote
import proto.vote_pb2_grpc as vote_grpc



tz = timezone(timedelta(hours=+8))
Voters = {}
Tokens = {}
Challenges = {}
Due = {}
Elections = {}
Ballots = {}

Voters, Tokens, Challenges, Due, Elections, Ballots

is_primary = 0

managerSOCK = None
managerCONN = None

def Sync(option): 
    '''
    option=0: primary > backup 
    option=1: backup > primary
    '''
    global managerCONN
    try:
        if is_primary ^ option:
            option = "SYNC " if option == 0 else "RESTORE "
            #print("[Server +] Syncronizing..")
            msg =   option + \
                    str(Voters) + "\x00" + \
                    str(Tokens) + "\x00" + \
                    str(Challenges) + "\x00" + \
                    str(Due) + "\x00" + \
                    str(Elections) + "\x00" + \
                    str(Ballots)
            managerCONN.send(msg.encode())
            print("[Server +] Send " + option + "done.")
        return
    except Exception as e:
        print("[Server -] Sync/Restore error: "+str(e))
        
def ManagerThread():    # loop forever recv()
    global managerSOCK
    global managerCONN
    global Voters, Tokens, Challenges, Due, Elections, Ballots
    global is_primary
    managerSOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    managerSOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    managerSOCK.bind(('', 50052))
    managerSOCK.listen(5)

    managerCONN, addr = managerSOCK.accept()
    print('[Server +] Connected by manager ' + str(addr))
    while True:
        try:
            command = managerCONN.recv(1024)
            if len(command) > 0:
                command = command.decode()
                op = command.split()[0]
                #print("op = "+op)
                if op == "PRIMARY":
                    is_primary = 1
                    print("[Server +] Primary here")

                elif op == "SYNC" or (op == "RESTORE" and is_primary):
                    # store data from manager
                    data = ''.join(command.split()[1:])
                    
                    Voters, Tokens, Challenges, Due, Elections, Ballots = [ast.literal_eval(line) for line in data.split('\x00')]
                    print("[Server +] "+op+" success.")
                    '''
                    print("store Voters : "+str(Voters))
                    print("store Tokens : "+str(Tokens))
                    print("store Challenges : "+str(Challenges))
                    print("store Due : "+str(Due))
                    print("store Elections : "+str(Elections))
                    print("store Ballots : "+str(Ballots))
                    print("--------")
                    '''
                elif op == "RESTORE" and is_primary == 0:
                    Sync(1)
            else:
                print("[Server -] Failed to connect to manager.")
                time.sleep(6)
                raise ConnectionResetError

        except KeyboardInterrupt:
            print("[Server -] Keyboard interrupt.")
            return
        except Exception as e:
            print("[Server -] ManagerThread error: "+str(e))

def checkToken(token):
    votername = list(Tokens.keys())[list(Tokens.values()).index(token)]
    if Due[votername] < int(datetime.now().timestamp()):
        del Tokens[votername]
        del Due[votername]
        Sync(0)
    return


def PopupWin(msg):
    popup = tk.Toplevel()
    popup.title("Message")
    popup.geometry('240x80+200+200')
    tk.Label(popup, text=msg, font=("Arial", 12)).pack()
    return


def RegisterVoter(name_var, group_var, key_var):
    global managerSOCK
    global managerCONN
    name = name_var.get()
    group = group_var.get()
    key = Base64Encoder.decode(key_var.get())
    try:
        if name not in Voters.keys():
            Voters[name] = (group, key)
            Sync(0)
            PopupWin("Register success!")
            return 0
        else:
            PopupWin("Voter Name already exists!")
            return 1
    except Exception as e:
        print("[Server -] Register voter error: " + str(e))
        PopupWin("Undefined error.")
        return 2


def UnregisterVoter(name_var):
    name = name_var.get()
    try:
        if name in Voters.keys():
            del Voters[name]
            Sync(0)
            PopupWin("Unregister Success!")
            return 0
        else:
            PopupWin("Voter Name does not exist!")
            return 1
    except:
        PopupWin("Undefined error.")
        return 2


def UpdateListBox(tree):
    for item in tree.get_children():
        tree.delete(item)
    count = 0
    for key, value in Voters.items():
        tree.insert('', 'end', text=count, values=(key, value[0]))
        count += 1


def UpdateElectionFrame():
    global elecframe
    for widget in elecframe.winfo_children():
        if widget.winfo_class() == 'Button':
            widget.destroy()
    
    for elecname, info in Elections.items():
        groups = " ".join([g for g in info[0]])
        btn = tk.Button(elecframe, text=elecname+"\n"+groups, font=("Arial", 16),
                        height = 4, width = 10)
        btn.pack(side = tk.LEFT, padx=20, pady=20)
    return


def RegisterThread():
    command = ""
    while command == "":
        reg_win = tk.Tk()
        reg_win.title("Voter Management")
        reg_win.geometry('640x520')

        # Input Voter name
        name_label = tk.Label(reg_win, text='Voter name :', font=("Arial", 12))
        name_label.place(relx=0.1, rely=0.1, relwidth=0.15, height=30)
        name_var = tk.StringVar()
        votername_textbox = tk.Entry(reg_win, textvariable=name_var, font=('Arial 16'))
        votername_textbox.place(relx=0.3, rely=0.1, relwidth=0.25, height=30)

        # Input Voter group
        group_label = tk.Label(
            reg_win, text='Voter group :', font=("Arial", 12))
        group_label.place(relx=0.1, rely=0.2, relwidth=0.15, height=30)
        group_var = tk.StringVar()
        votergroup_textbox = tk.Entry(reg_win, textvariable=group_var, font=('Arial 16'))
        votergroup_textbox.place(relx=0.3, rely=0.2, relwidth=0.25, height=30)

        # Input public key
        key_label = tk.Label(reg_win, text='Public key :', font=("Arial", 12))
        key_label.place(relx=0.1, rely=0.3, relwidth=0.15, height=30)
        key_var = tk.StringVar()
        key_textbox = tk.Entry(reg_win, textvariable=key_var, font=('Arial 16'))
        key_textbox.place(relx=0.3, rely=0.3, relwidth=0.25, height=30)

        # Voter list
        s = ttk.Style()
        s.theme_use('clam')
        # Add a Treeview widget
        tree = ttk.Treeview(reg_win, column=("c1", "c2"),
                            show='headings', height=10)

        tree.column("# 1", anchor=tk.CENTER, width=90)
        tree.heading("# 1", text="Name")
        tree.column("# 2", anchor=tk.CENTER, width=90)
        tree.heading("# 2", text="Group")

        count = 0
        for key, value in Voters.items():
            tree.insert('', 'end', text=count, values=(key, value[0]))
            count += 1

        tree.place(relx=0.65, rely=0.05, relwidth=0.3, relheight=0.55)

        # Button
        btn1 = tk.Button(reg_win, text="Register", font=("Arial", 16), command=lambda: [
                         RegisterVoter(name_var, group_var, key_var), UpdateListBox(tree)])
        btn1.place(relx=0.1, rely=0.48, relwidth=0.2, relheight=0.1)
        btn2 = tk.Button(reg_win, text="Unregister", font=("Arial", 16), command=lambda: [
                         UnregisterVoter(name_var), UpdateListBox(tree)])
        btn2.place(relx=0.4, rely=0.48, relwidth=0.2, relheight=0.1)
        
        global elecframe

        wrapper = ttk.LabelFrame(reg_win)
        
        canvas = tk.Canvas(wrapper,height=140)
        canvas.pack(side=tk.TOP, fill="x", expand="yes")
        
        scrollbar = ttk.Scrollbar(wrapper, orient="horizontal",command=canvas.xview)
        scrollbar.pack(side=tk.BOTTOM, fill="x")

        canvas.configure(xscrollcommand=scrollbar.set)
        canvas.bind('<Configure>',lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        elecframe = tk.Frame(canvas)
        #canvas.pack()
        canvas.create_window((0,0),window=elecframe, anchor="nw")

        #wrapper.place(relx=0, rely=0.7, relheight=0.25, relwidth=1)
        wrapper.pack(side=tk.BOTTOM, fill="x", expand="yes", anchor="s")

        '''
        canvas = tk.Canvas(reg_win)
        canvas.place(relx=0, rely=0.7, relheight=0.3, relwidth=1)
        scrollbar = ttk.Scrollbar(reg_win, orient="horizontal",command=canvas.xview)
        scrollbar.pack(side=tk.BOTTOM, fill="x")
        elecframe = ttk.Frame(canvas)
        #canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>',lambda e: elecframe.configure(scrollregion=elecframe.bbox("all")))
        elecframe.place(relx=0, rely=0, relheight=1, width=10000)
        '''
        UpdateElectionFrame()
        reg_win.mainloop()
        command = input(
            "<Press Enter to manage the voters> <Input any string to quit the management> ")
    return


def Count_Ballot(elecname):
    '''
    Ballots
    |   elect_name1
    |   |   voter1 : <his_choice>
    |   |   voter2 : <his_choice>
    |   |   .
    |   |   .
    |   elect_name2
    |   |   voter1 : <his_choice>
    |   |   voter1 : <his_choice>
    |   |
    '''
    choices = {}
    for selection in Ballots[elecname].values():
        choices[selection] = choices.get(selection, 0)+1

    return [vote.VoteCount(choice_name=choise, count=n) for choise, n in choices.items()]


class eVoting(vote_grpc.eVotingServicer):
    def PreAuth(self, request, context):
        name = request.name
        chal = os.urandom(4)
        Challenges[name] = chal
        Sync(0)
        return vote.Challenge(value=chal)

    def Auth(self, request, context):
        name = request.name.name
        response = request.response.value
        verify_key = VerifyKey(Voters[name][1])
        try:
            assert Challenges[name] == verify_key.verify(response)
            # PopupWin("Pass.")
            while True:
                b = os.urandom(4)
                if (b not in Tokens.values() and b != b'\x00\x00'):
                    Tokens[name] = b
                    break
            Due[name] = int((datetime.now()+timedelta(hours=1)).timestamp())
            Sync(0)
            return vote.AuthToken(value=b)
        except:
            PopupWin("Fail.")
            return vote.AuthToken(value=b'\x00\x00')

    def CreateElection(self, request, context):
        try:
            elecname = request.name
            token = request.token.value
            groups = request.groups
            choices = request.choices
            end_date = request.end_date
            checkToken(token)
            if not groups or not choices:
                #PopupWin("Missing groups or choices specification!")
                return vote.Status(code=2)
            if token not in Tokens.values():
                #PopupWin("invalid authentication token!")
                return vote.Status(code=1)
                
            print("[Server +] New election : "+elecname+", end at:" +
                    str(datetime.fromtimestamp(end_date.seconds).astimezone(tz)))
            Elections[elecname] = (groups, choices, end_date.seconds, token)
            Ballots[elecname] = {}
            Sync(0)
            #PopupWin("Election created successfully!")
            UpdateElectionFrame()
            return vote.Status(code=0)
                
        except Exception as e:
            #PopupWin("Undefined error.")
            print("[Server -] Create Election error: " + str(e))
            return vote.Status(code=3)

    def CastVote(self, request, context):
        '''
        Status.code=0 : Successful vote
        Status.code=1 : Invalid authentication token
        Status.code=2 : Invalid election name
        Status.code=3 : The voter's group is not allowed in the election
        Status.code=4 : A previous vote has been cast.
        '''
        
        try:
            token = request.token.value
            elecname = request.election_name
            votername = list(Tokens.keys())[list(Tokens.values()).index(token)]
            choice_name = request.choice_name
            checkToken(token)
            if token not in Tokens.values():
                return vote.Status(code=1)
            if elecname not in Elections.keys():
                return vote.Status(code=2)
            if Voters[votername][0] not in Elections[elecname][0]:
                return vote.Status(code=3)
                '''
                Ballots
                |   elect_name1
                |   |   voter1 : <his_choice>
                |   |   voter2 : <his_choice>
                |   |   .
                |   |   .
                |   elect_name2
                |   |   voter1 : <his_choice>
                |   |   voter1 : <his_choice>
                |   |
                '''
            if votername in Ballots[elecname].keys():
                return vote.Status(code=4)
            if choice_name not in Elections[elecname][1]:  # choice not exist
                return vote.Status(code=5)
            print("[Server +] New cast : " +votername+"->"+elecname+"->"+choice_name)
            Ballots[elecname][votername] = choice_name
            Sync(0)
            return vote.Status(code=0)

        except Exception as e:
            print("[Server -] Cast error: " + str(e))
            return vote.Status(code=5)

    def GetResult(self, request, context):
        '''
        ElectionReuslt.status = 0: Sucess
        ElectionResult.status = 1: Non-existent election
        ElectionResult.status = 2: The election is still ongoing. 
                                   Election result is not available yet.
        '''
        try:
            elecname = request.name
            timestamp = Timestamp()
            timestamp.FromDatetime(datetime.now().astimezone(tz))

            if elecname not in Elections.keys():
                return vote.ElectionResult(status=1, count=[])
            if Elections[elecname][2] > timestamp.seconds:
                return vote.ElectionResult(status=2, count=[])

            return vote.ElectionResult(status=0, count=Count_Ballot(elecname))
        except Exception as e:
            print("[Server -] Result query error: " + str(e))
            return vote.ElectionResult(status=3, count=[])


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    vote_grpc.add_eVotingServicer_to_server(eVoting(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    try:
        manager_thread = threading.Thread(target=ManagerThread, daemon=True)
        manager_thread.start()
        register_thread = threading.Thread(target=RegisterThread)
        register_thread.start()
        print("[Server +] Now serving..")
        serve()
    except KeyboardInterrupt:
        print("\n[Server] Terminated")
