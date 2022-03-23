all:
	python3 -m grpc_tools.protoc -I ./proto --python_out=./proto --grpc_python_out=./proto ./proto/vote.proto
clean:
	rm proto/vote_pb2_grpc.py proto/vote_pb2.py
server:
	@python3 server.py
client:
	@python3 client.py
