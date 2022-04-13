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

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from nacl.public import Box, PrivateKey
from nacl.signing import VerifyKey

import proto.vote_pb2 as vote
import proto.vote_pb2_grpc as vote_grpc

sys.path.append('proto')


tz = timezone(timedelta(hours=+8))
Tokens = {}
Due = deque()
Voters = {}
Elections = {}
Challenges = {}
Ballots = {}


def checkToken():
    while Due:
        if Due[0][0] < datetime.now():
            del Tokens[Due[0][1]]
            Due.popleft()


def PopupWin(msg):
    popup = tk.Toplevel()
    popup.title("Message")
    popup.geometry('240x80+200+200')
    tk.Label(popup, text=msg, font=("Arial", 12)).pack()
    return


def RegisterVoter(name_var, group_var, key_var):
    name = name_var.get()
    group = group_var.get()
    key = ast.literal_eval(key_var.get())
    try:
        if name not in Voters.keys():
            Voters[name] = (group, key)
            PopupWin("Register success!")
            return 0
        else:
            PopupWin("Voter Name already exists!")
            return 1
    except:
        PopupWin("Undefined error.")
        return 2


def UnregisterVoter(name_var):
    name = name_var.get()
    try:
        if name in Voters.keys():
            del Voters[name]
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


def RegisterThread():
    command = ""
    while command == "":
        reg_win = tk.Tk()
        reg_win.title("Voter Management")
        reg_win.geometry('640x320')

        # Input Voter name
        name_label = tk.Label(reg_win, text='Voter name :', font=("Arial", 12))
        name_label.place(relx=0.1, rely=0.18, relwidth=0.15, height=30)
        name_var = tk.StringVar()
        votername_textbox = tk.Entry(reg_win, textvariable=name_var)
        votername_textbox.place(relx=0.3, rely=0.18, relwidth=0.25, height=30)

        # Input Voter group
        group_label = tk.Label(
            reg_win, text='Voter group :', font=("Arial", 12))
        group_label.place(relx=0.1, rely=0.3, relwidth=0.15, height=30)
        group_var = tk.StringVar()
        votergroup_textbox = tk.Entry(reg_win, textvariable=group_var)
        votergroup_textbox.place(relx=0.3, rely=0.3, relwidth=0.25, height=30)

        # Input public key
        key_label = tk.Label(reg_win, text='Public key :', font=("Arial", 12))
        key_label.place(relx=0.1, rely=0.42, relwidth=0.15, height=30)
        key_var = tk.StringVar()
        key_textbox = tk.Entry(reg_win, textvariable=key_var)
        key_textbox.place(relx=0.3, rely=0.42, relwidth=0.25, height=30)

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

        tree.place(relx=0.65, rely=0.1, relwidth=0.3, relheight=0.8)

        # Button
        btn1 = tk.Button(reg_win, text="Register", font=("Arial", 16), command=lambda: [
                         RegisterVoter(name_var, group_var, key_var), UpdateListBox(tree)])
        btn1.place(relx=0.1, rely=0.7, relwidth=0.2, relheight=0.2)
        btn2 = tk.Button(reg_win, text="Unregister", font=("Arial", 16), command=lambda: [
                         UnregisterVoter(name_var), UpdateListBox(tree)])
        btn2.place(relx=0.4, rely=0.7, relwidth=0.2, relheight=0.2)

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
        return vote.Challenge(value=chal)

    def Auth(self, request, context):
        name = request.name.name
        response = request.response.value
        verify_key = VerifyKey(Voters[name][1])
        try:
            assert Challenges[name] == verify_key.verify(response)
            # PopupWin("Pass.")
            b = os.urandom(4)
            Tokens[name] = b
            Due.append([datetime.now()+timedelta(hours=1), name])
            return vote.AuthToken(value=b)
        except:
            PopupWin("Fail.")
            return vote.AuthToken(value=b'\x00\x00')

    def CreateElection(self, request, context):
        checkToken()
        try:
            elecname = request.name
            token = request.token.value
            if token in Tokens.items():
                try:
                    groups = request.groups
                    choices = request.choices
                    end_date = request.end_date
                    print("new election : "+elecname+", end at:" +
                          str(datetime.fromtimestamp(end_date.seconds).astimezone(tz)))
                    Elections[elecname] = (groups, choices, end_date, token)
                    Ballots[elecname] = {}
                    #PopupWin("Election created successfully!")
                    return vote.Status(code=0)
                except:
                    #PopupWin("Missing groups or choices specification!")
                    return vote.Status(code=2)
            else:
                #PopupWin("invalid authentication token!")
                return vote.Status(code=1)
        except Exception as e:
            #PopupWin("Undefined error.")
            print("Create Election error: " + str(e))
            return vote.Status(code=3)

    def CastVote(self, request, context):
        '''
        Status.code=0 : Successful vote
        Status.code=1 : Invalid authentication token
        Status.code=2 : Invalid election name
        Status.code=3 : The voter's group is not allowed in the election
        Status.code=4 : A previous vote has been cast.
        '''
        checkToken()
        try:
            token = request.token.value
            elecname = request.election_name
            votername = list(Tokens.keys())[list(Tokens.values()).index(token)]
            choice_name = request.choice_name
            print(votername+"->"+elecname+"->"+choice_name)
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
            Ballots[elecname][votername] = choice_name
            return vote.Status(code=0)

        except Exception as e:
            print("Cast error: " + str(e))
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
            if Elections[elecname][2].seconds > timestamp.seconds:
                return vote.ElectionResult(status=2, count=[])

            return vote.ElectionResult(status=0, count=Count_Ballot(elecname))
        except Exception as e:
            print("Result query error: " + str(e))
            return vote.ElectionResult(status=3, count=[])


def serve():
    print("Now serving..")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    vote_grpc.add_eVotingServicer_to_server(eVoting(), server)
    server.add_insecure_port('[::]:50051')
    server.start()
    server.wait_for_termination()


if __name__ == '__main__':
    logging.basicConfig()
    try:
        register_thread = threading.Thread(target=RegisterThread)
        register_thread.start()
        serve()
    except KeyboardInterrupt:
        register_thread.join()
        print("\nTerminated")
