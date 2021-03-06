from google.protobuf.timestamp_pb2 import Timestamp
import sys
sys.path.append('proto')
from nacl.signing import SigningKey
import proto.vote_pb2_grpc as vote_grpc
import proto.vote_pb2 as vote
import logging
import grpc
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime, timezone, timedelta
from nacl.encoding import Base64Encoder

tz = timezone(timedelta(hours=+8))
primaryIP = ""
backupIP  = ""
stub = [None,None,None]
channel = [None,None,None]
connecting_server = 0

def printc(str, color = 'white'):
    if color == 'red':
        print('\033[1;31m' + str + '\033[0;37m')
    elif color == 'green':
        print('\033[1;32m' + str + '\033[0;37m')
    elif color == 'yellow':
        print('\033[1;33m' + str + '\033[0;37m')
    else:
        print('\033[0;37m' + str + '\033[0;37m')

def SetConnection(funcName, param):
    global stub, connecting_server
    while True:
        try:
            grpc_call = getattr(stub[connecting_server], funcName)
            response = grpc_call(param)
            printc(f"[Client] Successfully connecting to {connecting_server}.", 'green')
            break
        except grpc._channel._InactiveRpcError:
            printc(f"[Client] Failed to connect to {connecting_server}.", 'red')
            connecting_server = -connecting_server
        except KeyboardInterrupt:
            print("[Client] Keyboard Interrupt.")
            break
        except Exception as e:
            printc("[Client] SetConnection error: "+str(e), 'red')
    return response

class VoterClass:
    def __init__(self):
        self.voter_name = ""
        #self.signing_key = SigningKey.generate()        # Generate a new random signing key
        self.signing_key = SigningKey(b'NNhdK95f3J3TVVzIC7BlLOdyMSvJWjKcXte2q4oVSVw=', encoder=Base64Encoder)
        '''
        private1:
            b'NNhdK95f3J3TVVzIC7BlLOdyMSvJWjKcXte2q4oVSVw='
        public1:
            b'5bkBKzX1bA7oEqZnUYhI5LliLrNxoereKxbNbwjfPEw='

        private2:
            b'0vWuClFMbtpV79oYxOJvz7okDrG4SlxsFhaxE7lpojo='
        public2:
            b'mbUv9IIv8tmI4Uc8oSbFUyCo78SCu8KOGAEmIhxe6rQ='

        private3:
            b'xJXRsCGd9hiV5zmJ5fiMbmbOXIqdezxjX574gW55AlQ='
        public3:
            b'BU036lSDeZvv6JdKq5WGd5ngDXFEBAFtZn1EVrJTXqM='
        '''
        self.verify_key = self.signing_key.verify_key   # Obtain the verify key for a given signing key
        self.auth_token = b'\x00\x00'


    def PopupWin(self,msg):
        popup = tk.Toplevel()
        popup.title("Message")
        popup.geometry('240x80+200+200')
        tk.Label(popup, text=msg, font=("Arial", 12)).pack()
        return


    def Button_Login(self, name_var, serverNum):
        global connecting_server
        connecting_server = serverNum.get()
        self.voter_name = name_var.get()

        self.log_win.destroy()


    def InputName(self):
        self.log_win = tk.Tk()
        self.log_win.title("Login")
        self.log_win.geometry('480x240')
        # Input Voter name
        name_label = tk.Label(self.log_win, text='Your name:', font=("Arial", 16))
        name_label.place(relx=0.2, rely=0.2, relwidth=0.25, height=30)
        name_var = tk.StringVar()
        votername_textbox = tk.Entry(self.log_win, textvariable=name_var, font=('Arial 16'))
        votername_textbox.place(relx=0.45, rely=0.2, relwidth=0.3, height=30)
        # Choose a server
        server_label = tk.Label(self.log_win, text='Server:', font=("Arial", 16))
        server_label.place(relx=0.2, rely=0.45, relwidth=0.25, height=30)
        serverNum = tk.IntVar() 
        rdioOne = tk.Radiobutton(self.log_win, text=' 1', variable=serverNum, value=1, 
                                    height=20, width=10, indicatoron=0, font=('Arial 16'), selectcolor='#40E0D0') 
        rdioOne.place(relx=0.5, rely=0.45, relwidth=0.1, height=30)
        rdioTwo = tk.Radiobutton(self.log_win, text='-1', variable=serverNum, value=-1, 
                                    height=20, width=10, indicatoron=0, font=('Arial 16'), selectcolor='#40E0D0')  
        rdioTwo.place(relx=0.6, rely=0.45, relwidth=0.1, height=30)
        rdioOne.select()

        btn1 = tk.Button(self.log_win, text="Login", command=lambda: self.Button_Login(name_var, serverNum))
        btn1.place(relx=0.4, rely=0.7, relwidth=0.2, relheight=0.2)
        self.log_win.mainloop()


    def TryAuth(self):
        chall = SetConnection("PreAuth", vote.VoterName(name=self.voter_name))
        signed = self.signing_key.sign(chall.value)
        resp = vote.Response(value=signed)
        auth_request = vote.AuthRequest(
            name=vote.VoterName(name=self.voter_name), 
            response=resp
            )
        response = SetConnection("Auth",auth_request)
        self.auth_token = response.value

    
    def Button_SendCreation(self, elecname_var, elecgroup_var, choices_var, etime_var):
        timestamp = Timestamp()
        dt = datetime.fromisoformat(etime_var.get()).astimezone(tz)
        timestamp.FromDatetime(dt)
        
        election_info = vote.Election(
            name = elecname_var.get(),
            groups = elecgroup_var.get().split(),
            choices = choices_var.get().split(),
            end_date = timestamp,
            token = vote.AuthToken(value=self.auth_token)
        )
        
        
        status = SetConnection("CreateElection",election_info).code
        
        if status==0:
            self.PopupWin("Election created successfully!")
            self.create_win.destroy()
        elif status==1:
            self.PopupWin("Invalid authentication token!")
            self.create_win.destroy()
        elif status==2:
            self.PopupWin("Missing groups or choices specification!")
        else:
            self.PopupWin("Undefined error.")


    def Button_CreateElection(self):
        self.create_win = tk.Toplevel()
        self.create_win.title("Create an election")
        self.create_win.geometry('640x560+200+200')

        #Title
        create_title = tk.Label(self.create_win, text='Create an election', font=("Arial", 20, 'bold'))
        create_title.place(relx=0.5, rely=0.1, relwidth=0.5, height=40, anchor=tk.CENTER)

        # Input Election name
        elecname_label = tk.Label(self.create_win, text='Election name :', font=("Arial", 12))
        elecname_label.place(relx=0.18, rely=0.2, relwidth=0.3, height=40)
        elecname_var = tk.StringVar()
        elecname_textbox = tk.Entry(self.create_win, textvariable=elecname_var, font=('Arial 16'))
        elecname_textbox.place(relx=0.5, rely=0.2, relwidth=0.35, height=40)

        # Input Election groups
        elecgroup_label = tk.Label(self.create_win, text='Election groups :\n(saperated by spaces)', font=("Arial", 12))
        elecgroup_label.place(relx=0.18, rely=0.3, relwidth=0.3, height=40)
        elecgroup_var = tk.StringVar()
        elecgroup_textbox = tk.Entry(self.create_win, textvariable=elecgroup_var, font=('Arial 16'))
        elecgroup_textbox.place(relx=0.5, rely=0.3, relwidth=0.35, height=40)

        # Input choices
        choices_label = tk.Label(self.create_win, text='Choices :\n(saperated by spaces)', font=("Arial", 12))
        choices_label.place(relx=0.18, rely=0.4, relwidth=0.3, height=40)
        choices_var = tk.StringVar()
        choices_textbox = tk.Entry(self.create_win, textvariable=choices_var, font=('Arial 16'))
        choices_textbox.place(relx=0.5, rely=0.4, relwidth=0.35, height=40)

        # Input end time
        etime_label = tk.Label(self.create_win, text='End time :\n(YYYY-MM-DD hh:mm:ss)', font=("Arial", 12))
        etime_label.place(relx=0.18, rely=0.5, relwidth=0.3, height=40)
        etime_var = tk.StringVar()
        etime_textbox = tk.Entry(self.create_win, textvariable=etime_var, font=('Arial 16'))
        etime_textbox.insert(0, "2022-04-10 17:00:00")
        etime_textbox.place(relx=0.5, rely=0.5, relwidth=0.35, height=40)

        # Send Creation Button
        btn1 = tk.Button(self.create_win, text="Create", font=("Arial", 16), command=lambda: 
                         self.Button_SendCreation(elecname_var, elecgroup_var, choices_var, etime_var))
        btn1.place(relx=0.5, rely=0.7, relwidth=0.2, relheight=0.1, anchor=tk.CENTER)

        self.create_win.mainloop()


    def Button_SendCast(self, elecname_var, choice_var):
        cast_info = vote.Vote(
            election_name = elecname_var.get(),
            choice_name = choice_var.get(),
            token = vote.AuthToken(value=self.auth_token)
        )
        
        status = SetConnection("CastVote", cast_info).code
        if status==0:
            self.PopupWin("Successful vote!")
            self.cast_win.destroy()
        elif status==1:
            self.PopupWin("Invalid authentication token!")
            self.cast_win.destroy()
        elif status==2:
            self.PopupWin("Invalid election name!")
        elif status==3:
            self.PopupWin("You are not allowed in the election!")
        elif status==4:
            self.PopupWin("A previous vote has been cast!")
        else:
            self.PopupWin("Undefined error.")


    def Button_CastVote(self):
        self.cast_win = tk.Toplevel()
        self.cast_win.title("Cast")
        self.cast_win.geometry('640x280+200+200')

        #Title
        cast_title = tk.Label(self.cast_win, text='Cast a vote', font=("Arial", 20, 'bold'))
        cast_title.place(relx=0.5, rely=0.1, relwidth=0.5, height=40, anchor=tk.CENTER)

        # Input Election name
        elecname_label = tk.Label(self.cast_win, text='Election name :', font=("Arial", 16))
        elecname_label.place(relx=0.18, rely=0.2, relwidth=0.3, height=40)
        elecname_var = tk.StringVar()
        elecname_textbox = tk.Entry(self.cast_win, textvariable=elecname_var, font=('Arial 16'))
        elecname_textbox.place(relx=0.5, rely=0.2, relwidth=0.35, height=40)

        # Input choices
        choice_label = tk.Label(self.cast_win, text='Choice :', font=("Arial", 16))
        choice_label.place(relx=0.18, rely=0.4, relwidth=0.3, height=40)
        choice_var = tk.StringVar()
        choice_textbox = tk.Entry(self.cast_win, textvariable=choice_var, font=('Arial 16'))
        choice_textbox.place(relx=0.5, rely=0.4, relwidth=0.35, height=40)

        # Send Cast Button
        btn1 = tk.Button(self.cast_win, text="Cast", font=("Arial", 16), command=lambda: 
                         self.Button_SendCast(elecname_var, choice_var))
        btn1.place(relx=0.5, rely=0.75, relwidth=0.2, relheight=0.2, anchor=tk.CENTER)

        self.cast_win.mainloop()


    def DrawPieChart(self, ballot_count):
        self.result_win = tk.Toplevel()
        self.result_win.title("Result")
        self.result_win.geometry('640x500+200+200')
        fig = plt.figure(figsize=(6, 6), dpi=100)
        fig.set_size_inches(6, 4)
        plt.rcParams.update({'font.size': 14})

        choice_label = [c.choice_name for c in ballot_count]
        choice_count = [c.count       for c in ballot_count]
        explode = [0.2 if win == max(choice_count) else 0 for win in choice_count]
        plt.pie(choice_count, explode=explode, labels=choice_label,  
            autopct='%1.1f%%', shadow=True, startangle=90)
        plt.axis('equal') # creates the pie chart like a circle
        canvasbar = FigureCanvasTkAgg(fig, master=self.result_win)
        canvasbar.draw()
        canvasbar.get_tk_widget().place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        plt.close()
        self.result_win.mainloop()
        

    def Button_SendQuery(self, elecname_var):
        query_info = vote.ElectionName(name = elecname_var.get())
        
        result = SetConnection("GetResult", query_info)
        status = result.status
        ballot_count = result.count
        if status==0:
            self.DrawPieChart(ballot_count)#show ballot_count
        elif status==1:
            self.PopupWin("Non-existent election!")
        elif status==2:
            self.PopupWin("The election is still ongoing.\nElection result is not available yet.")
        else:
            self.PopupWin("Undefined error.")

    def Button_VeiwResult(self):
        self.rst_win = tk.Toplevel()
        self.rst_win.title("Get Result")
        self.rst_win.geometry('640x180+200+200')

        #Title
        cast_title = tk.Label(self.rst_win, text='Get election result', font=("Arial", 20, 'bold'))
        cast_title.place(relx=0.5, rely=0.1, relwidth=0.5, height=40, anchor=tk.CENTER)

        # Input Election name
        elecname_label = tk.Label(self.rst_win, text='Election name :', font=("Arial", 16))
        elecname_label.place(relx=0.18, rely=0.3, relwidth=0.3, height=40)
        elecname_var = tk.StringVar()
        elecname_textbox = tk.Entry(self.rst_win, textvariable=elecname_var, font=('Arial 16'))
        elecname_textbox.place(relx=0.5, rely=0.3, relwidth=0.35, height=40)
        
        # Send Result Request Button
        btn1 = tk.Button(self.rst_win, text="Get result", font=("Arial", 16), command=lambda: 
                         self.Button_SendQuery(elecname_var))
        btn1.place(relx=0.5, rely=0.75, relwidth=0.2, relheight=0.2, anchor=tk.CENTER)

        self.rst_win.mainloop()



    def HomePage(self):
        self.home_win = tk.Tk()
        self.home_win.title("Home")
        self.home_win.geometry('640x280')

        #Title
        home_title = tk.Label(self.home_win, text='Welcome, '+self.voter_name+"!", font=("Arial", 20, 'bold'))
        home_title.place(relx=0.5, rely=0.15, relwidth=0.5, height=40, anchor=tk.CENTER)

        #Button
        btn1 = tk.Button(self.home_win, text="Create Election", font=("Arial",12), command=lambda: self.Button_CreateElection())
        btn1.place(relx=0.2, rely=0.6, relwidth=0.2, relheight=0.4, anchor=tk.CENTER)
        btn2 = tk.Button(self.home_win, text="Cast Vote",       font=("Arial",12), command=lambda: self.Button_CastVote())
        btn2.place(relx=0.5, rely=0.6, relwidth=0.2, relheight=0.4, anchor=tk.CENTER)
        btn3 = tk.Button(self.home_win, text="View Result"    , font=("Arial",12), command=lambda: self.Button_VeiwResult())
        btn3.place(relx=0.8, rely=0.6, relwidth=0.2, relheight=0.4, anchor=tk.CENTER)
        
        self.home_win.mainloop()        

if __name__ == '__main__':
    logging.basicConfig()
    primaryIP = input("IP:PORT for primary server : ")
    backupIP =  input("IP:PORT for backup  server : ")

    voter = VoterClass()
    print("Your public key:")
    print((voter.verify_key.encode(encoder=Base64Encoder)).decode("utf-8"))
    print("\nPlease register your info on the server.\nThen login in the popup window.")

    channel[1] = grpc.insecure_channel(primaryIP)
    stub[1] = vote_grpc.eVotingStub(channel[1])
    channel[-1] = grpc.insecure_channel(backupIP)
    stub[-1] = vote_grpc.eVotingStub(channel[-1])
    
    voter.InputName()
    voter.TryAuth()
    voter.HomePage()
