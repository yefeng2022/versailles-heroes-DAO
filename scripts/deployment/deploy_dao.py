import json

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
    history,
)

from . import deployment_config as config

# TODO set weights!

# name, type weight
typeWeight = 10 * 10 ** 17
GUILD_TYPES = [
    ("Gas MOH", "GASMOH", typeWeight),
]


def live_part_one():
    admin, _ = config.get_live_admin()
    deploy_part_one(admin, config.REQUIRED_CONFIRMATIONS, config.DEPLOYMENTS_JSON)


def live_part_two():
    admin, _ = config.get_live_admin()
    with open(config.DEPLOYMENTS_JSON) as fp:
        deployments = json.load(fp)
    token = ERC20VRH.at(deployments["ERC20VRH"])
    voting_escrow = VotingEscrow.at(deployments["VotingEscrow"])
    gas_escrow_template = GasEscrow.at(deployments["GasEscrowTemplate"])
    guild_template = Guild.at(deployments["GuildTemplate"])

    deploy_part_two(
        admin, token, voting_escrow, gas_escrow_template, guild_template, config.REQUIRED_CONFIRMATIONS, config.DEPLOYMENTS_JSON
    )


def development():
    token, voting_escrow, gas_escrow_template, guild_template = deploy_part_one(accounts[0])
    deploy_part_two(accounts[0], token, voting_escrow, gas_escrow_template, guild_template)


def deploy_part_one(admin, confs=1, deployments_json=None):
    token = ERC20VRH.deploy("Vote Escrowed Token", "VRH", 18, {"from": admin, "required_confs": confs})
    voting_escrow = VotingEscrow.deploy(
        token,
        "Voting-escrowed VRH",
        "veVRH",
        "veVRH_0.99",
        {"from": admin, "required_confs": confs},
    )
    gas_escrow_template = GasEscrow.deploy({"from": admin, "required_confs": confs})
    guild_template = Guild.deploy({"from": admin, "required_confs": confs})
    deployments = {
        "ERC20VRH": token.address,
        "VotingEscrow": voting_escrow.address,
        "GasEscrowTemplate": gas_escrow_template.address,
        "GuildTemplate": guild_template.address
    }
    if deployments_json is not None:
        with open(deployments_json, "w") as fp:
            json.dump(deployments, fp)
        print(f"Deployment addresses saved to {deployments_json}")

    return token, voting_escrow, gas_escrow_template, guild_template


def deploy_part_two(admin, token, voting_escrow, gas_escrow_template, guild_template, confs=1, deployments_json=None):
    guild_controller = GuildController.deploy(
        token, voting_escrow, guild_template, gas_escrow_template, {"from": admin, "required_confs": confs}
    )
    gas_token = ERC20Gas.deploy(
        "Gas Escrowed Token", 
        "MOH", 
        18, 
        {"from": admin, "required_confs": confs}
    )
    for name, type, weight in GUILD_TYPES:
        guild_controller.add_type(name, type, gas_token, weight, {"from": admin, "required_confs": confs})

    vesting = RewardVestingEscrow.deploy({"from": admin, "required_confs": confs})
    minter = Minter.deploy(token, guild_controller, vesting, {"from": admin, "required_confs": confs})
    token.set_minter(minter, {"from": admin, "required_confs": confs})
    vesting.set_minter(minter, {"from": admin, "required_confs": confs})

    deployments = {
        "ERC20VRH": token.address,
        "VotingEscrow": voting_escrow.address,
        "GasToken": gas_token.address,
        "GuildController": guild_controller.address,
        "Minter": minter.address
    }

    print(f"Deployment complete! Total gas used: {sum(i.gas_used for i in history)}")
    if deployments_json is not None:
        with open(deployments_json, "w") as fp:
            json.dump(deployments, fp)
        print(f"Deployment addresses saved to {deployments_json}")
