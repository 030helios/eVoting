# FTC_Part1
## Setup the environment
```
$ python -m pip install --upgrade pip
$ python -m pip install grpcio
$ python -m pip install grpcio-tools
```
## Make
`$ make`  
Regenerates the followings:  
`vote_pb2.py` which contains our generated request and response classes   
`vote_pb2_grpc.py` which contains our generated client and server classes.
## Run
### Run server first
`$ python3 server.py`  
or  
`$ make server`
### Run clients
`$ python3 client.py`  
or  
`$ make client`
