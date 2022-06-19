# FTC eVoting System
## Setup the environment
python 3.8
```
$ python -m pip install --upgrade pip
$ python -m pip install grpcio
$ python -m pip install grpcio-tools
$ sudo apt-get install python3-tk
$ pip install pynacl
$ pip install matplotlib
$ pip3 install varname
```
## Make
`$ make`  
Regenerates the followings:  
`vote_pb2.py` which contains our generated request and response classes.
`vote_pb2_grpc.py` which contains our generated client and server classes.
## Run
### Demo Link
https://youtu.be/eROVNXL8Ntw
### Run two server(primary & backup) first
`$ python3 server.py`  
### Run manager in primary's VM
`$ python3 manager.py`  
### Run clients
`$ python3 client.py`
### Create network partition
```
$ sudo iptables -A OUTPUT -d {VM1 IP} -j DROP
$ sudo iptables -I INPUT -s {VM1 IP} -j DROP
```
### Network reconnect
```
$ sudo iptables -F
```
## Quit the server
i)  Close all the windows then input any string in the terminal  
ii) Press Ctrl-C