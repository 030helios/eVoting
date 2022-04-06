from encodings import utf_8
from rsa import PublicKey
import nacl.utils
from nacl.signing import VerifyKey
from nacl.public import PrivateKey, Box
import tkinter as tk
from tkinter import ttk
import threading
import grpc
from tokenize import group
import logging
from concurrent import futures
import proto.vote_pb2 as vote
import proto.vote_pb2_grpc as vote_grpc
import sys
import os
import ast
sys.path.append('proto')


Tokens = {}
Voters = {}
Elections = {}
Challenges = {}


def popup(msg):
    popup = tk.Toplevel()
    popup.title("Message")
    popup.geometry('240x80+200+200')
    label = tk.Label(popup, text=msg)
    label.config(font=("Arial", 12))
    label.pack()
    return


def RegisterVoter(name_var, group_var, key_var):
    name = name_var.get()
    group = group_var.get()
    key = ast.literal_eval(key_var.get())
    try:
        if name not in Voters.keys():
            Voters[name] = (group, key)
            popup("Register success!")
            return 0
        else:
            popup("Voter Name already exists!")
            return 1
    except:
        popup("Undefined error.")
        return 2


def UnregisterVoter(name_var):
    name = name_var.get()
    try:
        if name in Voters.keys():
            del Voters[name]
            popup("Unregister Success!")
            return 0
        else:
            popup("Voter Name does not exist!")
            return 1
    except:
        popup("Undefined error.")
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
        reg_win.geometry('640x240')

        # Input Voter name
        name_label = tk.Label(reg_win, text='Voter name:')
        name_label.place(relx=0.05, rely=0.2, relwidth=0.15, height=30)
        name_var = tk.StringVar()
        votername_textbox = tk.Entry(reg_win, textvariable=name_var)
        votername_textbox.place(relx=0.25, rely=0.2, relwidth=0.25, height=30)

        # Input Voter group
        group_label = tk.Label(reg_win, text='Voter group:')
        group_label.place(relx=0.05, rely=0.3, relwidth=0.15, height=30)
        group_var = tk.StringVar()
        votergroup_textbox = tk.Entry(reg_win, textvariable=group_var)
        votergroup_textbox.place(relx=0.25, rely=0.3, relwidth=0.25, height=30)

        # Input public key
        key_label = tk.Label(reg_win, text='Public key:')
        key_label.place(relx=0.05, rely=0.4, relwidth=0.15, height=30)
        key_var = tk.StringVar()
        key_textbox = tk.Entry(reg_win, textvariable=key_var)
        key_textbox.place(relx=0.25, rely=0.4, relwidth=0.25, height=30)

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
        btn1 = tk.Button(reg_win, text="Register", command=lambda: [
                         RegisterVoter(name_var, group_var, key_var), UpdateListBox(tree)])
        btn1.place(relx=0.1, rely=0.7, relwidth=0.2, relheight=0.2)
        btn2 = tk.Button(reg_win, text="Unregister", command=lambda: [
                         UnregisterVoter(name_var), UpdateListBox(tree)])
        btn2.place(relx=0.4, rely=0.7, relwidth=0.2, relheight=0.2)

        reg_win.mainloop()
        command = input(
            "<Press Enter to manage the voters> <Input any string to quit the management> ")
    return


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
        if Challenges[name] == verify_key.verify(response):
            popup("Pass.")
            b = os.urandom(4)
            Tokens[name] = b
            return vote.AuthToken(value=b)
        else:
            popup("Fail.")
            return vote.AuthToken(value=b'\x00\x00')

    def CreateElection(self, request, context):
        try:
            name = request.name
            token = request.token.value
            if token == Tokens[name]:
                try:
                    groups = request.groups = 2
                    choices = request.choices = 3
                    end_date = request.end_date
                    Elections[name] = (groups, choices, end_date, token)
                    popup("Election created successfully!")
                    return vote.ElectionStatus(code=0)
                except:
                    popup("Missing groups or choices specification!")
                    return vote.ElectionStatus(code=2)
            else:
                popup("invalid authentication token!")
                return vote.ElectionStatus(code=1)
        except:
            popup("Undefined error.")
            return vote.ElectionStatus(code=3)

    def CastVote(self, request, context):
        return vote.VoteStatus(code=1)

    def GetResult(self, request, context):
        return vote.ElectionResult(status=1, count=0)


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
