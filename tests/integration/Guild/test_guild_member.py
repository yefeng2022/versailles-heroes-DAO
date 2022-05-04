import brownie
from tests.conftest import approx

import pytest
from test_guild_owner import create_guild

H = 3600
DAY = 86400
WEEK = 7 * DAY
MONTH = 4 * WEEK
MAXTIME = 126144000
TOL = 120 / WEEK


@pytest.fixture(scope="module", autouse=True)
def initial_setup(chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, vesting):
    alice, bob, carl = accounts[:3]
    amount_alice = 40000 * 10 ** 18
    amount_bob = 50000 * 10 ** 18
    amount_carl = 1000000 * 10 ** 18
    token.transfer(bob, amount_alice, {"from": alice})
    token.transfer(bob, amount_bob, {"from": alice})
    token.transfer(carl, amount_carl, {"from": alice})

    chain.sleep(DAY + 1)
    token.update_mining_parameters()

    token.approve(voting_escrow.address, amount_alice * 10, {"from": alice})
    token.approve(voting_escrow.address, amount_bob * 10, {"from": bob})
    token.approve(voting_escrow.address, amount_carl * 10, {"from": carl})

    # Move to timing which is good for testing - beginning of a UTC week
    chain.sleep((chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp)
    chain.mine()

    chain.sleep(H)

    voting_escrow.create_lock(amount_alice, chain[-1].timestamp + MAXTIME, {"from": alice})
    voting_escrow.create_lock(amount_bob, chain[-1].timestamp + MAXTIME, {"from": bob})
    voting_escrow.create_lock(amount_carl, chain[-1].timestamp + MAXTIME, {"from": carl})

    chain.sleep(H)
    chain.mine()

    token.set_minter(minter.address, {"from": accounts[0]})
    guild_controller.set_minter(minter.address, {"from": accounts[0]})
    vesting.set_minter(minter.address, {"from": accounts[0]})
    chain.sleep(10)


def test_join_guild_twice(chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, vesting, Guild):
    """
    Test join guild
    """
    alice = accounts[0]
    bob = accounts[1]
    guild = create_guild(chain, guild_controller, gas_token, alice, Guild)
    chain.sleep(60)
    chain.mine()
    # join guild for the first time
    guild.join_guild({"from": bob})
    chain.sleep(60)
    chain.mine()
    # join guild for the second time revert
    with brownie.reverts("Already in a guild"):
        guild.join_guild({"from": bob})


def test_leave_guild(chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, vesting, Guild):
    '''
    test leave guild voting power decrease, integrate fraction not change and only can claim vesting
    :return:
    '''
    alice = accounts[0]
    bob = accounts[1]
    guild = create_guild(chain, guild_controller, gas_token, alice, Guild)
    alice_voting_power = voting_escrow.balanceOf(alice)
    alice_slope = voting_escrow.get_last_user_slope(alice)
    chain.sleep(WEEK)
    chain.mine()
    # join guild
    guild.join_guild({"from": bob})
    chain.sleep(2 * WEEK + 1)
    chain.mine()
    # bob leave guild
    tx = guild.leave_guild({"from": bob})
    print(tx.events)
    # record integrate fraction
    integrate_fraction_after_leave_guild = guild.integrate_fraction(bob)
    chain.sleep(60)
    chain.mine()
    # check guild voting power decrease by bob's voting power
    next_time_voting_power = guild_controller.get_guild_weight(guild.address)
    # bob leave, left only alice, get alice voting power
    current_alice_power = alice_voting_power - alice_slope * (
        ((chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp + 3 * WEEK))

    assert approx(current_alice_power, next_time_voting_power, TOL)

    # advance to vesting epoch start
    chain.sleep((chain[-1].timestamp // MONTH + 1) * MONTH - chain[-1].timestamp)
    chain.mine()
    chain.sleep(WEEK)
    chain.mine()
    tx = minter.mint({"from": bob})
    print(tx.events)
    # integration fraction
    expect_integrate_fraction = guild.integrate_fraction(bob)
    assert integrate_fraction_after_leave_guild == expect_integrate_fraction


def test_increase_amount_guild_weight_increase(chain, accounts, token, gas_token, voting_escrow, guild_controller,
                                               minter, vesting, Guild):
    '''
    test_increase_amount_guild_weight_increase
    :return:
    '''
    alice = accounts[0]
    guild = create_guild(chain, guild_controller, gas_token, alice, Guild)

    chain.sleep(WEEK)
    chain.mine()
    increase_amount = 20000 * 10 ** 18
    voting_escrow.increase_amount(increase_amount, {"from": alice})
    alice_power_after_increase = voting_escrow.balanceOf(alice)
    alice_slope = voting_escrow.get_last_user_slope(alice)
    guild.update_working_balance(alice, {"from": alice})
    chain.sleep(10)
    chain.mine()
    # update working balance once more for check
    guild.update_working_balance(alice, {"from": alice})
    alice_power_at_next_time = alice_power_after_increase - alice_slope * (
            (chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp)
    guild_voting_weight = guild_controller.get_guild_weight(guild.address)
    assert approx(alice_power_at_next_time, guild_voting_weight, TOL)


def test_guild_earn_without_boosting(chain, accounts, token, gas_token, voting_escrow, guild_controller,
                                     minter, vesting, Guild, GasEscrow):
    # WIP
    alice = accounts[0]
    guild = create_guild(chain, guild_controller, gas_token, alice, Guild)

    chain.sleep(WEEK)
    chain.mine()
    tx = guild.update_working_balance(alice, {"from": alice})
    print("1st", tx.events)

    gas_escrow_contract = guild_controller.gas_addr_escrow(gas_token.address)
    # deposit game token to gas escrow and boost

    chain.sleep(WEEK)
    chain.mine()
    tx = guild.update_working_balance(alice, {"from": alice})
    print("2nd", tx.events)


def test_boosting(chain, accounts, token, gas_token, voting_escrow, guild_controller,
                                  minter, vesting, Guild, GasEscrow):
    # WIP
    alice = accounts[0]
    bob = accounts[1]
    carl = accounts[2]
    guild = create_guild(chain, guild_controller, gas_token, alice, Guild)

    # skip boost warm up
    chain.sleep(2 * WEEK)
    chain.mine()
    tx = guild.update_working_balance(alice, {"from": alice})
    print("----alice 1st", tx.events)

    chain.sleep(10)
    chain.mine()
    gas_amount = 100000 * 10 ** 18
    setup_gas_token(accounts, alice, gas_amount, gas_token, guild_controller, GasEscrow)
    tx = guild.update_working_balance(alice, {"from": alice})
    print("----alice 2nd", tx.events)

    tx = guild.join_guild({"from": carl})
    print('----carl 1st', tx.events)
    gas_amount_carl = 10000000 * 10 ** 18
    setup_gas_token(accounts, carl, gas_amount_carl, gas_token, guild_controller, GasEscrow)
    tx = guild.update_working_balance(carl, {"from": carl})
    print("----carl 2nd", tx.events)
    chain.sleep(WEEK)
    chain.mine()

    # bob join guild
    tx = guild.join_guild({"from": bob})
    print('----bob 1st', tx.events)
    # add gas for bob
    setup_gas_token(accounts, bob, gas_amount, gas_token, guild_controller, GasEscrow)
    tx = guild.update_working_balance(bob, {"from": bob})
    print("----bob second", tx.events)
    tx = guild.update_working_balance(alice, {"from": alice})
    print("----alice 3rd", tx.events)


def setup_gas_token(accounts, account, gas_amount, gas_token, guild_controller, GasEscrow):
    # deposit game token to gas escrow and boost
    gas_token.transfer(account, gas_amount, {"from": accounts[0]})
    gas_escrow_addr = guild_controller.gas_addr_escrow(gas_token.address)
    gas_token.approve(gas_escrow_addr, gas_amount * 10, {"from": account})
    gas_escrow_contract = GasEscrow.at(gas_escrow_addr)
    gas_escrow_contract.create_gas(gas_amount, {"from": account})
