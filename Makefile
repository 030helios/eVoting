all:
	python3 -m grpc_tools.protoc -I ./proto --python_out=./proto --grpc_python_out=./proto ./proto/vote.proto
clean:
	fuser -k 50052/tcp
	sudo iptables -F
server:
	@python3 server.py
client:
	@python3 client.py
manager:
	@python3 manager.py
part:
	sudo iptables -A OUTPUT -d 192.168.220.1 -j DROP