from __future__ import print_function
from nacl.signing import SigningKey
import proto.vote_pb2_grpc as vote_grpc
import proto.vote_pb2 as vote
import logging
import grpc
import sys
sys.path.append('proto')

signing_key = 0
verify_key = 0


def TryAuth(name):
    with grpc.insecure_channel('localhost:50051') as channel:
        vn = vote.VoterName(name=name)
        stub = vote_grpc.eVotingStub(channel)
        chall = stub.PreAuth(vn)

        signed = signing_key.sign(chall.value)
        res = vote.Response(value=signed)
        response = stub.Auth(vote.AuthRequest(name=vn, response=res))


def run():
    global signing_key
    global verify_key
    # Generate a new random signing key
    signing_key = SigningKey.generate()
    # Obtain the verify key for a given signing key
    verify_key = signing_key.verify_key
    print("verify_key:")
    print(verify_key)
    input("Press Enter to continue...")
    TryAuth("you")


if __name__ == '__main__':
    logging.basicConfig()
    run()
