import proto.vote_pb2_grpc as vote_grpc
import proto.vote_pb2 as vote
from concurrent import futures
import logging
from tokenize import group
import grpc
import sys

from rsa import PublicKey
sys.path.append('proto')


class eVoting(vote_grpc.eVotingServicer):
    def RegisterVoter(self, request, context):
        return vote.Voter(name='John', group='Student', PublicKey=b'\xDE\xAD')

    def UnregisterVoter(self, request, context):
        return vote.VoterName(name='John')

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
        serve()
    except KeyboardInterrupt:
        print("Terminated")
