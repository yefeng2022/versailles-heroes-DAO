import brownie

import pytest
from tests.conftest import approx

H = 3600
DAY = 86400
WEEK = 7 * DAY
MAXTIME = 126144000
TOL = 120 / WEEK


@pytest.fixture(scope="module", autouse=True)
def initial_setup(web3, chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, vesting):
    alice, bob = accounts[:2]
    amount_alice = 40000 * 10 ** 18
    amount_bob = 50000 * 10 ** 18
    token.transfer(bob, amount_alice, {"from": alice})
    token.transfer(bob, amount_bob, {"from": alice})
    stages = {}

    chain.sleep(DAY + 1)
    token.update_mining_parameters()

    token.approve(voting_escrow.address, amount_alice * 10, {"from": alice})
    token.approve(voting_escrow.address, amount_bob * 10, {"from": bob})

    assert voting_escrow.totalSupply() == 0
    assert voting_escrow.balanceOf(alice) == 0
    assert voting_escrow.balanceOf(bob) == 0

    # Move to timing which is good for testing - beginning of a UTC week
    chain.sleep((chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp)
    chain.mine()

    chain.sleep(H)

    stages["before_deposits"] = (web3.eth.blockNumber, chain[-1].timestamp)

    voting_escrow.create_lock(amount_alice, chain[-1].timestamp + MAXTIME, {"from": alice})
    voting_escrow.create_lock(amount_bob, chain[-1].timestamp + MAXTIME, {"from": bob})
    stages["alice_deposit"] = (web3.eth.blockNumber, chain[-1].timestamp)

    chain.sleep(H)
    chain.mine()

    token.set_minter(minter.address, {"from": accounts[0]})
    guild_controller.set_minter(minter.address, {"from": accounts[0]})
    vesting.set_minter(minter.address, {"from": accounts[0]})
    chain.sleep(10)


def test_create_guild(chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, vesting, Guild):
    """
    Test create guild
    """
    alice = accounts[0]
    guild_obj = create_guild(chain, guild_controller, gas_token, alice, Guild)

    curr_time = chain[-1].timestamp
    next_time = (chain[-1].timestamp // WEEK + 1) * WEEK
    print("prev time:", curr_time // WEEK * WEEK)
    print("curr_time: ", curr_time)
    print("next_time: ", next_time)
    relative_weight_curr_time = guild_controller.guild_relative_weight(guild_obj.address, curr_time, {"from": alice})
    assert relative_weight_curr_time == 0
    relative_weight_next_time = guild_controller.guild_relative_weight(guild_obj.address, next_time, {"from": alice})
    assert relative_weight_next_time == 1 * 10 ** 18  # expected 100% since there is only 1 guild


def test_guild_mining(chain, accounts, token, gas_token, voting_escrow, guild_template, guild_controller, minter,
                      vesting, Guild):
    '''
    test guild mining of guild owner
    :return:
    '''
    alice = accounts[0]
    guild_alice = create_guild(chain, guild_controller, gas_token, alice, Guild)
    chain.sleep(3 * WEEK)
    tx = guild_alice.update_working_balance(alice, {"from": alice})
    print(tx.events)
    # print("checkpoint event", tx.events['CheckpointValues'], "\n")
    accumulate_rewards = guild_alice.integrate_fraction(alice)
    print("accumulate_rewards before mint", accumulate_rewards)
    tx = minter.mint({"from": alice})
    print("mint event log", tx.events['Minted'])
    mint_event = tx.events['Minted']
    vesting_locked = mint_event['vesting_locked']
    minted = mint_event['minted']
    assert approx(vesting_locked + minted, accumulate_rewards, TOL)


def test_join_guild_and_vote_for_guild(chain, accounts, token, gas_token, voting_escrow, guild_template,
                                       guild_controller, minter,
                                       vesting, Guild):
    '''
    test join guild and vote increased in next time
    :return:
    '''
    alice = accounts[0]
    bob = accounts[1]
    guild = create_guild(chain, guild_controller, gas_token, alice, Guild)

    chain.sleep(60)
    # record guild voting power before bob join
    guild_weight_before_bob_join = guild_controller.get_guild_weight(guild.address)
    # bob join guild
    guild.join_guild({"from": bob})

    # check bob in this guild_member_list
    assert guild.address == guild_controller.global_member_list(bob)
    # bob voting power to decrease
    bob_slope = voting_escrow.get_last_user_slope(bob)
    bob_decrease = bob_slope * ((chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp)
    bob_voting_power = voting_escrow.balanceOf(bob) - bob_decrease
    # check voting balance of guild in next time is added to guild
    guild_weight_after_bob_join = guild_controller.get_guild_weight(guild.address)
    assert guild_weight_before_bob_join + bob_voting_power == guild_weight_after_bob_join
    # next epoch
    chain.sleep((chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp + 10)
    chain.mine()
    # check guild weight taking effect
    guild_controller.checkpoint({"from": alice})
    guild_curr_weight = guild_controller.guild_effective_weight(guild.address)
    assert guild_curr_weight == guild_weight_after_bob_join


def test_set_commission_rate(chain, accounts, gas_token, guild_controller, Guild):
    alice = accounts[0]
    bob = accounts[1]
    guild = create_guild(chain, guild_controller, gas_token, alice, Guild)
    # TODO 2 Weeks can not change commission rate?
    chain.sleep(2 * WEEK + 1)
    chain.mine()
    with brownie.reverts("Only guild owner can change commission rate"):
        guild.set_commission_rate(False, {"from": bob})

    with brownie.reverts("Maximum is 20"):
        guild.set_commission_rate(True, {"from": alice})

    tx = guild.set_commission_rate(False, {"from": alice})
    assert tx.events["SetCommissionRate"]["commission_rate"] == 19
    chain.sleep(600)
    chain.mine()
    with brownie.reverts("Can only change commission rate once every week"):
        guild.set_commission_rate(False, {"from": alice})


def test_transfer_ownership(chain, accounts, gas_token, guild_controller, Guild):
    alice = accounts[0]
    bob = accounts[1]
    guild = create_guild(chain, guild_controller, gas_token, alice, Guild)

    chain.sleep(WEEK + 1)
    chain.mine()
    # check guild controller global owner list is alice
    assert guild.address == guild_controller.guild_owner_list(alice)
    with brownie.reverts("New owner is not in the same guild"):
        guild_controller.transfer_guild_ownership(bob, {"from": alice})
    # bob join guild as a member
    guild.join_guild({"from": bob})
    # transfer ownership to bob
    guild_controller.transfer_guild_ownership(bob, {"from": alice})
    # check guild controller global owner list is bob
    assert guild.address == guild_controller.guild_owner_list(bob)


def test_owner_leave_guild(chain, accounts, gas_token, guild_controller, Guild):
    alice = accounts[0]
    guild = create_guild(chain, guild_controller, gas_token, alice, Guild)

    chain.sleep(2 * WEEK + 1)
    chain.mine()
    with brownie.reverts("Owner cannot leave guild"):
        guild.leave_guild({"from": alice})


def create_guild(chain, guild_controller, gas_token, guild_owner, Guild):
    guild_type = 0
    commission_rate = 20
    type_weight = 1 * 10 ** 18
    guild_controller.add_type("Gas MOH", "GASMOH", gas_token.address, type_weight)
    chain.sleep(H)
    guild_controller.create_guild(guild_owner, guild_type, commission_rate, {"from": guild_owner})
    guild_address = guild_controller.guild_owner_list(guild_owner)
    guild_contract = Guild.at(guild_address)
    guild_contract.update_working_balance(guild_owner, {"from": guild_owner})
    return guild_contract
