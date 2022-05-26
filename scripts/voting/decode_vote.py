import warnings

from brownie import Contract
from hexbytes import HexBytes

warnings.filterwarnings("ignore")

# the vote ID you wish to decrypt
VOTE_ID = 0

# address of the contract where the vote was created
# ownership votes: 0x1A0B896824fB45983c9bC6183795D9c89682F446
# parameter votes: 0xbcff8b0b9419b9a88c44546519b1e909cf330399
#VOTING_ADDRESS = "0x1A0B896824fB45983c9bC6183795D9c89682F446"
VOTING_ADDRESS = "0xb18811c42adb9fe8048c4912d137640ab3c79131"


def main(vote_id=VOTE_ID):
    print("decode vote:")
    print("vote address:", VOTING_ADDRESS)
    print("vote id:", vote_id)
    proxy = Contract.from_explorer(VOTING_ADDRESS)
    if hasattr(proxy, 'implementation'):
        aragon = Contract.from_explorer(VOTING_ADDRESS, as_proxy_for=proxy.implementation())
    else:
        aragon = proxy

    evm_script = aragon.getVote(vote_id)
    print("evm_script:")
    print("open: %s, executed: %s, startDate: %s, snapshotBlock: %s" % (evm_script['open'], evm_script['executed'], evm_script['startDate'], evm_script['snapshotBlock']))
    print("supportRequired: %s, minAcceptQuorum: %s" % (evm_script['supportRequired'], evm_script['minAcceptQuorum']))
    print("yea: %s, nay: %s, votingPower: %s" % (evm_script['yea'], evm_script['nay'], evm_script['votingPower']))
    print("script: ", evm_script['script'])
    print()
    script = HexBytes(evm_script['script'])
    #script = HexBytes('0x00000001dd16b55d2db5c25a3e27cb5263d91d66efb64aa7000000640a8ed3db000000000000000000000000b18811c42adb9fe8048c4912d137640ab3c79131000000000000000000000000b18811c42adb9fe8048c4912d137640ab3c79131ad15e7261800b4bb73f1b69d3864565ffb1fd00cb93cf14fe48da8f1f2149f39')
    script = HexBytes('0x00000001dd16b55d2db5c25a3e27cb5263d91d66efb64aa700000064afd925df000000000000000000000000e5e94f76cb6c7f250780319a786ecf94d8ccf2e6000000000000000000000000b18811c42adb9fe8048c4912d137640ab3c79131da3972983e62bdf826c4b807c4c9c2b8a941e1f83dfa76d53d6aeac11e1be650')
    script = HexBytes('0x00000001dd16b55d2db5c25a3e27cb5263d91d66efb64aa7000000640a8ed3db000000000000000000000000b18811c42adb9fe8048c4912d137640ab3c79131000000000000000000000000b18811c42adb9fe8048c4912d137640ab3c79131ad15e7261800b4bb73f1b69d3864565ffb1fd00cb93cf14fe48da8f1f2149f39')
    
    idx = 4
    while idx < len(script):
        #target = Contract.from_explorer(script[idx : idx + 20])
        #if hasattr(target, 'implementation'):
        #    target = Contract.from_explorer(script[idx : idx + 20], as_proxy_for=target.implementation())
        
        print("decode contract: ", script[idx : idx + 20])
        target = Contract(script[idx : idx + 20])
        idx += 20
        length = int(script[idx : idx + 4].hex(), 16)
        idx += 4
        calldata = script[idx : idx + length]
        idx += length
        fn, inputs = target.decode_input(calldata)
        if calldata[:4].hex() == "0xb61d27f6":
            agent_target = Contract(inputs[0])
            fn, inputs = agent_target.decode_input(inputs[2])
            print(
                f"Call via agent ({target}):\n ├─ To: {agent_target}\n"
                f" ├─ Function: {fn}\n └─ Inputs: {inputs}\n"
            )
        else:
            print(f"Direct call:\n ├─ To: {target}\n ├─ Function: {fn}\n └─ Inputs: {inputs}")
