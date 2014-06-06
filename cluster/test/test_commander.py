from cluster import *
from . import utils
import mock


class Tests(utils.ComponentTestCase):

    def setUp(self):
        super(Tests, self).setUp()
        self.cb_args = None
        self.leader = mock.Mock(name='leader')
        self.slot = 10
        self.proposal = Proposal(caller='cli', client_id=123, input='inc')
        self.ballot_num = Ballot(91, 82)
        self.cmd = Commander(
            self.node, leader=self.leader, ballot_num=self.ballot_num,
            slot=self.slot, proposal=self.proposal,
            peers=['p1', 'p2', 'p3'])
        self.accept_message = Accept(slot=self.slot, ballot_num=self.ballot_num,
                                     proposal=self.proposal)

    def test_retransmit(self):
        """After start(), the commander sends ACCEPT repeatedly to all peers which have not responded"""
        self.cmd.start()
        self.assertMessage(['p1', 'p2', 'p3'], self.accept_message)
        self.network.tick(ACCEPT_RETRANSMIT)
        self.assertMessage(['p1', 'p2', 'p3'], self.accept_message)

        self.node.fake_message(
                Accepted(slot=self.slot, acceptor='p2', ballot_num=self.ballot_num))
        self.network.tick(ACCEPT_RETRANSMIT)
        self.assertMessage(['p1', 'p3'], self.accept_message)
        self.network.tick(ACCEPT_RETRANSMIT)
        self.assertMessage(['p1', 'p3'], self.accept_message)
        self.node.fake_message(
            Accepted(slot=self.slot, acceptor='p1', ballot_num=self.ballot_num))

        # quorum (3/2+1 = 2) reached
        self.assertMessage(['p1', 'p2', 'p3'], Decision(slot=self.slot, proposal=self.proposal))

        self.leader.commander_finished.assert_called_with(self.slot, self.ballot_num, False)
        self.assertTimers([])
        self.assertUnregistered()

    def test_wrong_slot(self):
        """Commander ignores ACCEPTED messages for other commanders"""
        self.cmd.start()
        self.assertMessage(['p1', 'p2', 'p3'], self.accept_message)
        other_slot = 999
        self.node.fake_message(
            Accepted(slot=other_slot, acceptor='p1', ballot_num=self.ballot_num))
        self.network.tick(ACCEPT_RETRANSMIT)
        # p1 still in the list
        self.assertMessage(['p1', 'p2', 'p3'], self.accept_message)

    def test_preempted(self):
        """If the commander receives an ACCEPTED response with a different ballot number, then it
        is preempted"""
        self.cmd.start()
        self.assertMessage(['p1', 'p2', 'p3'], self.accept_message)
        other_ballot_num = Ballot(99, 99)
        self.node.fake_message(
            Accepted(slot=self.slot, acceptor='p1', ballot_num=other_ballot_num))

        self.leader.commander_finished.assert_called_with(self.slot, other_ballot_num, True)
        self.assertTimers([])
        self.assertUnregistered()
