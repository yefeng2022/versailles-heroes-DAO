import json

from brownie import ERC20VRH, GuildController, VotingEscrow

from . import deployment_config as config


def live():
    admin, _ = config.get_live_admin()
    with open(config.DEPLOYMENTS_JSON) as fp:
        deployments = json.load(fp)

    transfer_ownership(
        admin,
        config.OWNERSHI_AGENT,
        config.CREATEGUILD_AGENT,
        deployments["GuildController"],
        deployments["VotingEscrow"],
        deployments["RewardVestingEscrow"],
        deployments["ERC20VRH"],
        config.REQUIRED_CONFIRMATIONS,
    )


def development():
    #  only works on a forked mainnet after the previous stages have been completed
    admin, _ = config.get_live_admin()
    with open(config.DEPLOYMENTS_JSON) as fp:
        deployments = json.load(fp)

    transfer_ownership(
        admin,
        config.OWNERSHI_AGENT,
        config.CREATEGUILD_AGENT,
        deployments["GuildController"],
        deployments["VotingEscrow"],
        deployments["RewardVestingEscrow"],
        deployments["ERC20VRH"],
    )


def transfer_ownership(
    admin, new_admin, create_guild_admin, guild_controller, voting_escrow, vesting, erc20vrh, confs=1
):
    guild_controller = GuildController.at(guild_controller)
    voting_escrow = VotingEscrow.at(voting_escrow)
    erc20vrh = ERC20VRH.at(erc20vrh)

    guild_controller.commit_transfer_ownership(new_admin, {"from": admin, "required_confs": confs})
    guild_controller.apply_transfer_ownership({"from": admin, "required_confs": confs})

    guild_controller.commit_transfer_create_guild_ownership(create_guild_admin, {"from": admin, "required_confs": confs})
    guild_controller.apply_transfer_create_guild_ownership({"from": admin, "required_confs": confs})

    voting_escrow.commit_transfer_ownership(new_admin, {"from": admin, "required_confs": confs})
    voting_escrow.apply_transfer_ownership({"from": admin, "required_confs": confs})

    erc20vrh.set_admin(new_admin, {"from": admin, "required_confs": confs})
    vesting.set_admin(new_admin, {"from": admin, "required_confs": confs})