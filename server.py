import sys
sys.path.append('proto')
import proto.vote_pb2_grpc as vote_grpc
import proto.vote_pb2 as vote
from concurrent import futures
import logging
from tokenize import group
import grpc
import threading
import tkinter as tk
from tkinter import ttk

from rsa import PublicKey

Voters = {}

def popup(msg):
    popup = tk.Toplevel()
    popup.title("Message")
    popup.geometry('240x80+200+200')
    label = tk.Label(popup, text=msg)
    label.config(font=("Arial", 12))
    label.pack()
    return


def RegisterVoter(name_var, group_var):
    name = name_var.get()
    group = group_var.get()
    try:
        if name not in Voters.keys():
            Voters[name] = (group, b'\xDE\xAD')
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
        tree.insert('','end',text=count,values=(key,value[0]))
        count+=1


def RegisterThread():
    command = ""
    while command == "":
        reg_win = tk.Tk()
        reg_win.title("Voter Management")
        reg_win.geometry('640x240')
        
        #Input Voter name
        name_label = tk.Label(reg_win, text='Voter name:')
        name_label.place(relx=0.05, rely=0.2, relwidth=0.15, height=30)
        name_var = tk.StringVar()
        votername_textbox = tk.Entry(reg_win, textvariable=name_var)
        votername_textbox.place(relx=0.25, rely=0.2, relwidth=0.25, height=30)

        #Input Voter group
        group_label = tk.Label(reg_win, text='Voter group:')
        group_label.place(relx=0.05, rely=0.4, relwidth=0.15, height=30)
        group_var = tk.StringVar()
        votergroup_textbox = tk.Entry(reg_win, textvariable=group_var)
        votergroup_textbox.place(relx=0.25, rely=0.4, relwidth=0.25, height=30)

        #Voter list
        s = ttk.Style()
        s.theme_use('clam')
        # Add a Treeview widget
        tree = ttk.Treeview(reg_win, column=("c1", "c2"), show='headings', height=10)

        tree.column("# 1", anchor=tk.CENTER, width=90)
        tree.heading("# 1", text="Name")
        tree.column("# 2", anchor=tk.CENTER, width=90)
        tree.heading("# 2", text="Group")

        count = 0
        for key, value in Voters.items():
            tree.insert('','end',text=count,values=(key,value[0]))
            count+=1

        tree.place(relx=0.65, rely=0.1, relwidth=0.3, relheight=0.8)

        #Button
        btn1 = tk.Button(reg_win, text="Register", command=lambda:[RegisterVoter(name_var,group_var),UpdateListBox(tree)])
        btn1.place(relx=0.1, rely=0.7, relwidth=0.2, relheight=0.2)
        btn2 = tk.Button(reg_win, text="Unregister", command=lambda:[UnregisterVoter(name_var),UpdateListBox(tree)])
        btn2.place(relx=0.4, rely=0.7, relwidth=0.2, relheight=0.2)

        reg_win.mainloop()
        command = input("<Press Enter to manage the voters> <Input any string to quit the management> ")
    return

class eVoting(vote_grpc.eVotingServicer):
    def PreAuth(self, request, context):
        return vote.Challenge(value=b'\xDE\xAD')

    def Auth(self, request, context):
        return vote.AuthToken(value=b'\xDE\xAD')

    def CreateElection(self, request, context):
        return vote.ElectionStatus(code=1)

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
        register_thread = threading.Thread(target = RegisterThread)
        register_thread.start()
        serve()
    except KeyboardInterrupt:
        register_thread.join()
        print("\nTerminated")
