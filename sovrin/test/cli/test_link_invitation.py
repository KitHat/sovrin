import json

import pytest

from plenum.test.eventually import eventually
from plenum.test.pool_transactions.helper import buildPoolClientAndWallet
from sovrin.client.wallet.attribute import Attribute
from sovrin.client.wallet.attribute import LedgerStore
from sovrin.client.wallet.link_invitation import LinkInvitation
from sovrin.client.wallet.wallet import Wallet
from sovrin.common.txn import USER, ATTRIB, ENDPOINT, SPONSOR
from sovrin.test.cli.helper import ensureConnectedToTestEnv
from sovrin.test.cli.conftest import getLinkInvitation
from sovrin.test.helper import genTestClient, makeNymRequest, makeAttribRequest, \
    makePendingTxnsRequest, createNym, TestClient

# noinspection PyUnresolvedReferences
from plenum.test.conftest import poolTxnStewardData, poolTxnStewardNames
from sovrin.test.test_client import addAttributeAndCheck


@pytest.fixture(scope="module")
def stewardClientAndWallet(poolNodesCreated, looper, tdirWithDomainTxns,
                           poolTxnStewardData):
    client, wallet = buildPoolClientAndWallet(poolTxnStewardData,
                                              tdirWithDomainTxns,
                                              clientClass=TestClient,
                                              walletClass=Wallet)
    client.registerObserver(wallet.handleIncomingReply)

    looper.add(client)
    looper.run(client.ensureConnectedToNodes())
    makePendingTxnsRequest(client, wallet)
    return client, wallet


@pytest.fixture(scope="module")
def aliceConnected(aliceCli, be, do, poolNodesCreated):

    # Done to initialise a wallet.
    # TODO: a wallet should not be required for connecting, right?
    be(aliceCli)
    do("new key")

    ensureConnectedToTestEnv(aliceCli)
    return aliceCli


def addNym(client, wallet, nym, role=USER):
    return makeNymRequest(client, wallet, nym, role)


def addFabersEndpoint(looper, client, wallet, nym, attrName, attrValue):
    val = json.dumps({attrName: attrValue})
    attrib = Attribute(name='Faber Endpoint',
                       origin=wallet.defaultId,
                       value=val,
                       dest=nym,
                       ledgerStore=LedgerStore.RAW)
    addAttributeAndCheck(looper, client, wallet, attrib)


def checkIfEndpointReceived(aCli, linkName, expStr):
    assert expStr in aCli.lastCmdOutput
    assert "Usage" in aCli.lastCmdOutput
    assert 'show link "{}"'.format(linkName) in aCli.lastCmdOutput
    assert 'accept invitation "{}"'.format(linkName) in aCli.lastCmdOutput
    if "Endpoint received" in expStr:
        li = getLinkInvitation("Faber", aCli)
        assert li.targetEndPoint is not None


def testShowFileNotExists(aliceCli, be, do, fileNotExists, faberMap):
    be(aliceCli)
    do("show {invite-not-exists}", expect=fileNotExists, mapper=faberMap)


def testShowFile(aliceCli, be, do, faberMap):
    be(aliceCli)
    do("show {invite}", expect="link-invitation",
                        not_expect="Given file does not exist",
                        mapper=faberMap)


def testLoadFileNotExists(aliceCli, be, do, fileNotExists, faberMap):
    be(aliceCli)
    do("load {invite-not-exists}", expect=fileNotExists, mapper=faberMap)


def testLoadFile(faberInviteLoaded):
    pass


def testLoadSecondFile(faberInviteLoaded, acmeInviteLoaded):
    pass


def testLoadExistingLink(aliceCli, be, do, faberInviteLoaded,
                         linkAlreadyExists, faberMap):
    be(aliceCli)
    do("load {invite}", expect=linkAlreadyExists, mapper=faberMap)


def testShowLinkNotExists(aliceCli, be, do, linkNotExists, faberMap):
    be(aliceCli)
    do("show link {inviter-not-exists}", expect=linkNotExists, mapper=faberMap)


def testShowFaberLink(aliceCli, faberInviteLoaded, be, do, faberMap, showLinkOut):
    be(aliceCli)
    do("show link {inviter}", expect=showLinkOut, mapper=faberMap)


def testShowAcmeLink(aliceCli, acmeInviteLoaded, be, do, acmeMap, showLinkOut):
    be(aliceCli)
    expected = showLinkOut + ["Claim Requests: ",
                              "Job Application"]
    do("show link {inviter}", expect=expected, mapper=acmeMap)


def testSyncLinkNotExists(aliceCli, be, do, linkNotExists, faberMap):
    be(aliceCli)
    do("sync {inviter-not-exists}", expect=linkNotExists, mapper=faberMap)


def testAliceConnect(aliceConnected):
    pass


@pytest.fixture(scope="module")
def faberAdded(poolNodesCreated,
             looper,
             aliceCli,
             faberInviteLoaded,
             aliceConnected,
             stewardClientAndWallet):
    client, wallet = stewardClientAndWallet
    li = getLinkInvitation("Faber", aliceCli)
    createNym(looper, li.targetIdentifier, client, wallet, role=SPONSOR)


def testSyncLinkWhenEndpointNotAvailable(faberAdded,
                                         looper,
                                         aliceCli,
                                         stewardClientAndWallet):
    li = getLinkInvitation("Faber", aliceCli)
    aliceCli.enterCmd("sync Faber")
    looper.run(eventually(checkIfEndpointReceived, aliceCli, li.name,
                          "Endpoint not available",
                          retryWait=1,
                          timeout=10))


def testSyncLinkWhenEndpointIsAvailable(looper,
                                        aliceCli,
                                        stewardClientAndWallet,
                                        faberAdded):
    client, wallet = stewardClientAndWallet
    li = getLinkInvitation("Faber", aliceCli)
    assert li.targetEndPoint is None
    endpointValue = "0.0.0.0:0000"
    addFabersEndpoint(looper, client, wallet, li.targetIdentifier,
                      ENDPOINT, endpointValue)
    aliceCli.enterCmd("sync Faber")
    looper.run(eventually(checkIfEndpointReceived, aliceCli, li.name,
                          "Endpoint received: {}".format(endpointValue),
                          retryWait=1,
                          timeout=10))
