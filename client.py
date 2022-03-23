from __future__ import print_function
import logging
import grpc
import sys, os
sys.path.append(os.path.abspath('./proto'))
import proto.vote_pb2 as vote
import proto.vote_pb2_grpc as vote_grpc


def run():
    # NOTE(gRPC Python Team): .close() is possible on a channel and should be
    # used in circumstances in which the with statement does not fit the needs
    # of the code.
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = vote_grpc.eVotingStub(channel)
        response = stub.PreAuth(vote.VoterName(name='you'))
    print(response.value)

if __name__ == '__main__':
    logging.basicConfig()
    run()