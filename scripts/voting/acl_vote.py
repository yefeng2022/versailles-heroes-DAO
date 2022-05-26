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
    "agent": "0x60db471e3c4d875d03ea1a2774b3fbaba97af67c",
    "voting": "0x7b86480fe5169197cb697363363cbda4c7058e26",
    "token": "0xfbF37F43d82E1240c11A2065C606bd414d07B888",
    "quorum": 30,
}

# address to create the vote from - you will need to modify this prior to mainnet use
accounts.add(config['wallets']['from_keys'])
SENDER = accounts[0]

guildType = 0
guildRate = 20
ACTIONS = [
    # ("name", "target", "fn_name", *args),
    ### grantPermission(address _entity, address _app, bytes32 _role, {'from': Account})
    ("aragon-acl", "0xbe9519fa1e90120f5713fa32abaafbab8f93aec7", "grantPermission", "0x7b86480fe5169197cb697363363cbda4c7058e26", "0xdfc7a15b7f8d951f9842ed3d116c4586c0791b87", "0xda3972983e62bdf826c4b807c4c9c2b8a941e1f83dfa76d53d6aeac11e1be650")

    ### createPermission(address _entity, address _app, bytes32 _role, address _manager, {'from': Account})
    #("aragon-acl", "0xbe9519fa1e90120f5713fa32abaafbab8f93aec7", "createPermission", "0x7b86480fe5169197cb697363363cbda4c7058e26", "0xdfc7a15b7f8d951f9842ed3d116c4586c0791b87", "ad15e7261800b4bb73f1b69d3864565ffb1fd00cb93cf14fe48da8f1f2149f39", "0x7b86480fe5169197cb697363363cbda4c7058e26")
    ### revokePermission(address _entity, address _app, bytes32 _role, {'from': Account})
    #("aragon-acl", "0xbe9519fa1e90120f5713fa32abaafbab8f93aec7", "revokePermission", "0xdfc7a15b7f8d951f9842ed3d116c4586c0791b87", "0xdfc7a15b7f8d951f9842ed3d116c4586c0791b87", "ad15e7261800b4bb73f1b69d3864565ffb1fd00cb93cf14fe48da8f1f2149f39")
    
    ### setPermissionManager(address _newManager, address _app, bytes32 _role, {'from': Account})
    #("aragon-acl", "0xbe9519fa1e90120f5713fa32abaafbab8f93aec7", "setPermissionManager", "0x7155fa7cFB7D965d74d10250B59B1eE1a4b0eDd1", "0xdfc7a15b7f8d951f9842ed3d116c4586c0791b87", "ad15e7261800b4bb73f1b69d3864565ffb1fd00cb93cf14fe48da8f1f2149f39")
]

# description of the vote, will be pinned to IPFS
DESCRIPTION = "A description of the vote."

def get_abi(name):
    with open("abi/%s.abi" % name, "r") as f:
        aragon_abi = json.loads(f.read())
    return aragon_abi

def prepare_evm_script():
    evm_script = "0x00000001"

    for name, address, fn_name, *args in ACTIONS:
        abi_info = get_abi(name)
        contract = Contract.from_abi(name, address, abi_info)
        fn = getattr(contract, fn_name)
        calldata = fn.encode_input(*args)[2:]
        length = hex(len(calldata) // 2)[2:].zfill(8)
        evm_script = f"{evm_script}{contract.address[2:]}{length}{calldata}"

    print(evm_script)
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
