# Testnet deployment script

import json
import time

from brownie import (
    ERC20VRH,
    ERC20Gas,
    GasEscrow,
    Guild,
    GuildController,
    Minter,
    RewardVestingEscrow,
    VotingEscrow,
    config,
    accounts,
    web3,
    network,
)
from web3 import middleware
from web3.gas_strategies.time_based import fast_gas_price_strategy as gas_strategy

USE_STRATEGIES = False  # Needed for the ganache-cli tester which doesn't like middlewares
POA = True

CONFS = 1
SaveAbi = True
ChangeToArago = False

ARAGON_AGENT = config['paramers']['aragon_agent']

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

# name, type weight
typeWeight = 10 * 10 ** 17
GUILD_TYPES = [
    ("Gas MOH", "GASMOH", typeWeight),
]

if network.show_active() != "development":
    DEPLOYER = config['paramers']['deployer']
    funding_admins = config['paramers']['funding_admins'].split(',')
else:
    DEPLOYER = accounts[1]
    funding_admins = accounts[1:5]

def repeat(f, *args):
    """
    Repeat when geth is not broadcasting (unaccounted error)
    """
    while True:
        try:
            return f(*args)
        except KeyError:
            continue


def save_abi(contract, name):
    with open("abi/%s.abi" % name, "w") as f:
        json.dump(contract.abi, f)


def main():
    if USE_STRATEGIES:
        web3.eth.setGasPriceStrategy(gas_strategy)
        web3.middleware_onion.add(middleware.time_based_cache_middleware)
        web3.middleware_onion.add(middleware.latest_block_based_cache_middleware)
        web3.middleware_onion.add(middleware.simple_cache_middleware)
        if POA:
            web3.middleware_onion.inject(middleware.geth_poa_middleware, layer=0)

    accounts.add(config['wallets']['from_keys'])
    print("accounts: %s" % len(accounts))
    deployer = accounts.at(DEPLOYER)
    print("deployer: %s, balance: %s" % (deployer, deployer.balance()))

    # deploy VRH and voting_escrow and gas_token.
    token = repeat(
        ERC20VRH.deploy,
        "Vote Escrowed Token",
        "VRH",
        18,
        {"from": deployer, "required_confs": CONFS}
    )
    if SaveAbi:
        save_abi(token, "token")

    voting_escrow = repeat(
        VotingEscrow.deploy,
        token,
        "Voting-escrowed VRH",
        "veVRH",
        "veVRH_0.99",
        {"from": deployer, "required_confs": CONFS}
    )
    save_abi(voting_escrow, "voting_escrow")

    gas_token = repeat(
        ERC20Gas.deploy,
        "Gas Escrowed Token",
        "MOH",
        18,
        {"from": deployer, "required_confs": CONFS}
    )
    if SaveAbi:
        save_abi(gas_token, "gas_token")

    # deploy guild_controller
    gas_escrow_template = repeat(
        GasEscrow.deploy,
        {"from": deployer, "required_confs": CONFS}
    )
    guild_template = repeat(
        Guild.deploy,
        {"from": deployer, "required_confs": CONFS}
    )
    guild_controller = repeat(
        GuildController.deploy,
        token,
        voting_escrow,
        guild_template,
        gas_escrow_template,
        {"from": deployer, "required_confs": CONFS}
    )
    if SaveAbi:
        save_abi(guild_controller, "guild_controller")

    # deploy vesting and minter
    now = time.time()
    """" old init.
    vesting = repeat(
        RewardVestingEscrow.deploy,
        token,
        now + 300,
        now + 300 + 100000000,
        False,
        funding_admins,
        {"from": deployer, "required_confs": CONFS}
    ) """
    vesting = repeat(
        RewardVestingEscrow.deploy,
        {"from": deployer, "required_confs": CONFS}
    )
    if SaveAbi:
        save_abi(vesting, "vesting")
    minter = repeat(
        Minter.deploy,
        token,
        guild_controller,
        vesting,
        {"from": deployer, "required_confs": CONFS}
    )
    if SaveAbi:
        save_abi(minter, "minter")

    # setting minter
    repeat(token.set_minter, minter, {"from": deployer, "required_confs": CONFS})
    repeat(guild_controller.set_minter, minter, {"from": deployer, "required_confs": CONFS})
    repeat(vesting.set_minter, minter, {"from": deployer, "required_confs": CONFS})

    # add type
    repeat(guild_controller.add_type, GUILD_TYPES[0][0], GUILD_TYPES[0][1], gas_token, GUILD_TYPES[0][2], {"from": deployer, "required_confs": CONFS})

    # print info
    print("now:", now)
    print("token: %s" % token)
    print("gas_token: %s" % gas_token)
    print("guild_controller: %s" % guild_controller)
    print("voting_escrow: %s" % voting_escrow)
    print("vesting: %s" % vesting)
    print("minter: %s" % minter)
    print("gas_escrow_template: %s" % gas_escrow_template)
    print("guild_template: %s" % guild_template)
    print("")


    if ChangeToArago:
        # guild_controller transfer ownership to ARAGON_AGENT
        repeat(guild_controller.commit_transfer_ownership, ARAGON_AGENT, {"from": deployer, "required_confs": CONFS})
        repeat(guild_controller.apply_transfer_ownership, {"from": deployer, "required_confs": CONFS})

        # voting_escrow transfer ownership to ARAGON_AGENT
        repeat(voting_escrow.commit_transfer_ownership, ARAGON_AGENT, {"from": deployer, "required_confs": CONFS})
        repeat(voting_escrow.apply_transfer_ownership, {"from": deployer, "required_confs": CONFS})

        # vesting transfer ownership to ARAGON_AGENT
        repeat(vesting.commit_transfer_ownership, ARAGON_AGENT, {"from": deployer, "required_confs": CONFS})
        repeat(vesting.apply_transfer_ownership, {"from": deployer, "required_confs": CONFS})