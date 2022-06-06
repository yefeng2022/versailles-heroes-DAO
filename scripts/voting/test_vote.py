import json
import warnings

import requests
from brownie import Contract, accounts, chain, config

warnings.filterwarnings("ignore")

# this script is used to prepare, simulate and broadcast votes within Versailles's DAO
# modify the constants below according the the comments, and then use `simulate` in
# a forked mainnet to verify the result of the vote prior to broadcasting on mainnet

# addresses related to the DAO - these should not need modification
# as_proxy_for=0xa4D1a2693589840BABb7f3A44D14Fdf41b3bF1Fe (voting)
# as_proxy_for=0xa4D1a2693589840BABb7f3A44D14Fdf41b3bF1Fe (agent)
TARGET = {
    #"forwarder": "0x8ea2cdaa10531b98ab2b4d122b9f3801663c35ec",
    "agent": "0x8f0d638c884f3d743bce0bb63ad5cfdc2159d340",
    "voting": "0xb18811c42adb9fe8048c4912d137640ab3c79131",
    "token": "0xfbF37F43d82E1240c11A2065C606bd414d07B888",
    "quorum": 30,
}

# address to create the vote from - you will need to modify this prior to mainnet use
#accounts.add(config['wallets']['from_keys'])
accounts.add('0xce8a45f212b737683743264b05e20ae57595c7c299c77155e8ffe70b9b4ed991')
SENDER = accounts[0]

# a list of calls to perform in the vote, formatted as a lsit of tuples
# in the format (target, function name, *input args).
#
# for example, to call:
# GaugeController("0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB").add_gauge("0xFA712...", 0, 0)
#
# use the following:
# [("0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB", "add_gauge", "0xFA712...", 0, 0),]
#
# commonly used addresses:
# GuildController - 0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB
# Guild - 0x519AFB566c05E00cfB9af73496D00217A630e4D5
# GasEscrow - 0xeCb456EA5365865EbAb8a2661B0c503410e9B347

guildType = 0
guildRate = 20
ACTIONS = [
    # ("target", "fn_name", *args),
    #("voting_escrow", "0xF4B87E521759c93877dec0b31b17fE9f1805782E", "name")
    #("voting_escrow", "0xF4B87E521759c93877dec0b31b17fE9f1805782E", "commit_transfer_ownership", "0x7155fa7cFB7D965d74d10250B59B1eE1a4b0eDd1")
    #("guild_controller", "0x33DeFdCbe3056b98c90dF05369e6A4b3281445E5", "create_guild", accounts[0], guildType, guildRate)
    #("aragon-acl", "0x8ea2cdaa10531b98ab2b4d122b9f3801663c35ec", "grantPermission", "0x17680a1a2a14dd50184db35aab322cc23814998e", "0x7155fa7cFB7D965d74d10250B59B1eE1a4b0eDd1", "0xda3972983e62bdf826c4b807c4c9c2b8a941e1f83dfa76d53d6aeac11e1be650")
    #("aragon-acl", "0xBe9519fa1e90120f5713FA32AbAAFbaB8F93AEC7", "setPermissionManager", "0x7155fa7cFB7D965d74d10250B59B1eE1a4b0eDd1", "0xdfC7A15b7f8d951f9842Ed3D116C4586c0791B87", "e7ab0252519cd959720b328191bed7fe61b8e25f77613877be7070646d12daf0")
    #("aragon-acl", "0x8ea2cdaa10531b98ab2b4d122b9f3801663c35ec", "grantPermission", "0x7155fa7cFB7D965d74d10250B59B1eE1a4b0eDd1", '0x7155fa7cFB7D965d74d10250B59B1eE1a4b0eDd1', '0xe7ab0252519cd959720b328191bed7fe61b8e25f77613877be7070646d12daf0')
    #("aragon-ownership-voting", "0xc087ee91b7f993ba36f2a82b0dae8e32169cedd4", "MODIFY_QUORUM_ROLE", '0x7155fa7cFB7D965d74d10250B59B1eE1a4b0eDd1')

    ("aragon-acl", "0xdd16b55d2db5c25a3e27cb5263d91d66efb64aa7", "grantPermission", "0xb18811c42adb9fe8048c4912d137640ab3c79131", "0x7155fa7cFB7D965d74d10250B59B1eE1a4b0eDd1", "ad15e7261800b4bb73f1b69d3864565ffb1fd00cb93cf14fe48da8f1f2149f39")
]

# description of the vote, will be pinned to IPFS
DESCRIPTION = "A description of the vote."

def get_abi(name):
    with open("abi/%s.abi" % name, "r") as f:
        aragon_abi = json.loads(f.read())
    return aragon_abi

def prepare_evm_script():
    # agent = Contract.from_explorer(TARGET["agent"])
    aragon_abi = get_abi("aragon-agent")
    agent = Contract.from_abi("agent", TARGET["agent"], aragon_abi)
    evm_script = "0x00000001"

    for name, address, fn_name, *args in ACTIONS:
        abi_info = get_abi(name)
        contract = Contract.from_abi(name, address, abi_info)
        fn = getattr(contract, fn_name)
        calldata = fn.encode_input(*args)
        agent_calldata = agent.execute.encode_input(address, 0, calldata)[2:]
        length = hex(len(agent_calldata) // 2)[2:].zfill(8)
        evm_script = f"{evm_script}{agent.address[2:]}{length}{agent_calldata}"

    return evm_script


def make_vote(sender=SENDER):
    text = json.dumps({"text": DESCRIPTION})
    # response = requests.post("https://ipfs.infura.io:5001/api/v0/add", files={"file": text}, auth=(infura_id, infura_secret))
    # ipfs_hash = response.json()["Hash"]  # QmRS6nMcnwQcYuP3JExDdrqsx3rrQxVFayVD8sHn2vGoV9
    ipfs_hash = "QmRS6nMcnwQcYuP3JExDdrqsx3rrQxVFayVD8sHn2vGoV9"
    print(f"ipfs hash: {ipfs_hash}")

    # aragon = Contract.from_explorer(TARGET["agent"], as_proxy_for=TARGET["voting"])
    proxy = Contract.from_explorer(TARGET["voting"])
    if hasattr(proxy, 'implementation'):
        aragon = Contract.from_explorer(TARGET["voting"], as_proxy_for=proxy.implementation())
    else:
        aragon = proxy
    #aragon = Contract(TARGET["voting"])
    evm_script = prepare_evm_script()
    #evm_script = '0x000000018ea2cdaa10531b98ab2b4d122b9f3801663c35ec000000640a8ed3db00000000000000000000000017680a1a2a14dd50184db35aab322cc23814998e0000000000000000000000007155fa7cFB7D965d74d10250B59B1eE1a4b0eDd1ad15e7261800b4bb73f1b69d3864565ffb1fd00cb93cf14fe48da8f1f2149f39'
    print("vote numbers: %s", aragon.votesLength())
    if TARGET.get("forwarder"):
        # the emergency DAO only allows new votes via a forwarder contract
        # so we have to wrap the call in another layer of evm script
        vote_calldata = aragon.newVote.encode_input(evm_script, DESCRIPTION, False, False)[2:]
        length = hex(len(vote_calldata) // 2)[2:].zfill(8)
        evm_script = f"0x00000001{aragon.address[2:]}{length}{vote_calldata}"
        print(f"Target: {TARGET['forwarder']}\nEVM script: {evm_script}")
        tx = Contract(TARGET["forwarder"]).forward(evm_script, {"from": sender})
    else:
        print(f"Target: {aragon.address}\nEVM script: {evm_script}")
        tx = aragon.newVote(
            evm_script,
            f"ipfs:{ipfs_hash}",
            False,
            False,
            {"from": sender, "priority_fee": "2 gwei"},
        )

    vote_id = tx.events["StartVote"]["voteId"]

    print(f"\nSuccess! Vote ID: {vote_id}")
    return vote_id


def simulate():
    # make the new vote
    convex = "0x989aeb4d175e16225e39e87d0d97a3360524ad80"
    vote_id = make_vote(convex)

    # vote
    proxy = Contract.from_explorer(TARGET["voting"])
    if hasattr(proxy, 'implementation'):
        aragon = Contract.from_explorer(TARGET["voting"], as_proxy_for=proxy.implementation())
    else:
        aragon = proxy
    aragon.vote(vote_id, True, False, {"from": convex})

    # sleep for a week so it has time to pass
    chain.sleep(86400 * 7)

    # moment of truth - execute the vote!
    aragon.executeVote(vote_id, {"from": accounts[0]})


def main():
    print("accounts: ", SENDER.address, SENDER.balance(), SENDER.private_key)
    vote_id = make_vote(sender=SENDER)
    print("please vote id: %s" % vote_id)
