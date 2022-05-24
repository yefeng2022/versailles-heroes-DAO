import brownie

import pytest
from tests.conftest import approx
from random import randrange
from brownie import ZERO_ADDRESS
from brownie_tokens import ERC20

H = 3600
DAY = 86400
WEEK = 7 * DAY
MAXTIME = 126144000
TOL = 120 / WEEK


@pytest.fixture(scope="module", autouse=True)
def initial_setup(web3, chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, reward_vesting):
    alice, bob = accounts[:2]
    amount_alice = 110000 * 10 ** 18
    amount_bob = 110000 * 10 ** 18
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

    stages["before_deposits"] = (web3.eth.block_number, chain[-1].timestamp)

    voting_escrow.create_lock(amount_alice, chain[-1].timestamp + MAXTIME, {"from": alice})
    voting_escrow.create_lock(amount_bob, chain[-1].timestamp + MAXTIME, {"from": bob})
    stages["alice_deposit"] = (web3.eth.block_number, chain[-1].timestamp)

    chain.sleep(H)
    chain.mine()

    token.set_minter(minter.address, {"from": accounts[0]})
    guild_controller.set_minter(minter.address, {"from": accounts[0]})
    reward_vesting.set_minter(minter.address, {"from": accounts[0]})
    chain.sleep(10)


def test_create_guild(chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, reward_vesting,
                      Guild):
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
                      reward_vesting, Guild):
    '''
    test guild mining of guild owner
    :return:
    '''
    alice = accounts[0]
    guild_alice = create_guild(chain, guild_controller, gas_token, alice, Guild)
    chain.sleep(3 * WEEK)
    tx = guild_alice.user_checkpoint(alice, {"from": alice})
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
                                       reward_vesting, Guild):
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


def test_bonus_for_owner(chain, accounts, token, gas_token, guild_controller, Guild):
    '''
    |_______|_______|_______|_______|_______|_
      1     2       3       4       5       6
    1. create_guild at 1
    2. bob join at 2
    3. check rewards between 2 and 3
    4. change commission rate between 3 and 4
    5. check rewards between 4 and 5
    6. check rewards at 5
    |_______| mean 1 WEEK
    '''
    alice = accounts[0]
    bob = accounts[1]
    # alice is owner at 1
    guild = create_guild(chain, guild_controller, gas_token, alice, Guild)
    rate = token.rate()

    # advance to 2
    chain.sleep((chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp)
    chain.mine()
    effective_timestamp = (chain[-1].timestamp // 100) * 100

    # bob join guild at 2
    guild.join_guild({"from": bob})
    dt = randrange(1, WEEK)
    chain.sleep(dt)
    chain.mine()

    # check rewards between 2 and 3
    # expect alice and bob get same rewards apart from owner bonus
    guild.user_checkpoint(alice, {"from": alice})
    guild.user_checkpoint(bob, {"from": bob})
    chain.sleep(10)
    chain.mine()
    commission_rate = guild.commission_rate(effective_timestamp)
    alice_bonus = rate * dt * commission_rate // 100
    alice_bonus_1 = guild.total_owner_bonus(alice)
    assert approx(alice_bonus, alice_bonus_1, TOL)

    # advance to 3
    elapsed_time = (chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp
    chain.sleep(elapsed_time)
    chain.mine()
    elapsed_time += 10
    chain.sleep(10)
    chain.mine()

    # alice change commission rate to 19% between 3 and 4
    guild.set_commission_rate(False, {"from": alice})
    next_time = effective_timestamp + 2 * WEEK
    assert guild.commission_rate(next_time) == 19
    assert guild.last_change_rate() == next_time

    # advance to 4, check in this epoch rewards still 20%
    elapsed_time += (chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp
    chain.sleep((chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp)
    chain.mine()
    guild.user_checkpoint(alice, {"from": alice})
    alice_checkpoint_reward_2 = guild.integrate_fraction(alice)
    alice_bonus_2 = guild.total_owner_bonus(alice)
    expected_bonus = rate * elapsed_time * commission_rate // 100
    assert approx(expected_bonus, alice_bonus_2 - alice_bonus_1, TOL)

    # commission rate 19% start apply at 4
    commission_rate = guild.commission_rate(next_time)
    dt = randrange(1, WEEK)
    chain.sleep(dt)
    chain.mine()

    expected_alice_bonus = rate * dt * commission_rate // 100
    # check rewards between 4 and 5
    guild.user_checkpoint(bob, {"from": bob})
    guild.user_checkpoint(alice, {"from": alice})
    alice_checkpoint_reward_3 = guild.integrate_fraction(alice)
    bob_checkpoint_reward_3 = guild.integrate_fraction(bob)
    alice_rewards_3 = alice_checkpoint_reward_3 - alice_checkpoint_reward_2
    alice_bonus_3 = guild.total_owner_bonus(alice)
    assert approx(expected_alice_bonus, alice_bonus_3 - alice_bonus_2, TOL)

    # record alice owner bonus
    alice_owner_bonus = guild.total_owner_bonus(alice)
    # transfer ownership to bob between 4 and 5
    guild_controller.transfer_guild_ownership(bob, {"from": alice})
    # advance to 5
    dt = (chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp
    chain.sleep(dt)
    chain.mine()
    # check rewards at 5
    guild.user_checkpoint(bob, {"from": bob})
    guild.user_checkpoint(alice, {"from": alice})
    alice_checkpoint_reward_4 = guild.integrate_fraction(alice)
    bob_checkpoint_reward_4 = guild.integrate_fraction(bob)
    alice_rewards_4 = alice_checkpoint_reward_4 - alice_checkpoint_reward_3
    bob_rewards_4 = bob_checkpoint_reward_4 - bob_checkpoint_reward_3
    bob_bonus = rate * dt * commission_rate // 100
    assert approx(bob_rewards_4 - bob_bonus, alice_rewards_4, TOL)
    # assert guild.total_owner_bonus(alice) == alice_owner_bonus
    assert approx(guild.total_owner_bonus(alice), alice_owner_bonus, TOL)
    assert approx(bob_bonus, guild.total_owner_bonus(bob), TOL)


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

    chain.sleep(10 * DAY + 1)
    chain.mine()
    # bob can not leave guild as a guild owner
    with brownie.reverts("Owner cannot leave guild"):
        guild.leave_guild({"from": bob})

    # bob transfer owner to ZERO_address
    guild_controller.transfer_guild_ownership(ZERO_ADDRESS, {"from": bob})
    assert guild_controller.guild_owner_list(bob) == ZERO_ADDRESS
    chain.sleep(DAY + 1)
    chain.mine()
    # bob leave guild
    guild.leave_guild({"from": bob})
    guild.leave_guild({"from": alice})
    chain.sleep(10)
    # alice create guild as owner
    guild2 = create_guild_only(accounts, alice, 10, 0, Guild, guild_controller)
    # check guild controller global owner list is alice
    assert guild2.address == guild_controller.guild_owner_list(alice)
    # bob create guild as owner
    guild3 = create_guild_only(accounts, bob, 10, 0, Guild, guild_controller)
    assert guild3.address == guild_controller.guild_owner_list(bob)


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
    guild_contract.user_checkpoint(guild_owner, {"from": guild_owner})
    return guild_contract


def create_type(type_id, guild_controller, type_weight):
    token_name = "Coin " + str(type_id)
    token_symbol = "MOH" + str(type_id)
    token_contract = ERC20(token_name, token_symbol, 18)

    token_type_name = "GAS" + token_name
    token_type_symbol = "GAS" + token_symbol
    tx = guild_controller.add_type(token_type_name, token_type_symbol, token_contract.address, type_weight)
    assert guild_controller.gas_addr_escrow(token_contract.address) == tx.events['AddType']['gas_escrow']


def create_guild_only(accounts, guild_owner, commission_rate, guild_type, Guild, guild_controller):
    guild_controller.create_guild(guild_owner, guild_type, commission_rate, {"from": accounts[0]})
    guild_address = guild_controller.guild_owner_list(guild_owner)
    guild_contract = Guild.at(guild_address)
    guild_contract.user_checkpoint(guild_owner, {"from": guild_owner})
    return guild_contract
