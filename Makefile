all:
	python3 -m grpc_tools.protoc -I ./proto --python_out=./proto --grpc_python_out=./proto ./proto/vote.proto
clean:
	fuser -k 50052/tcp
server:
	@python3 server.py
client:
	@python3 client.py
manager:
	@python3 manager.py
part:
	sudo iptables -A OUTPUT -d $(IP) -j DROP
	sudo iptables -I INPUT -s $(IP) -j DROP
reconnect:
	sudo iptables -F