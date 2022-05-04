import random

from brownie import chain
from brownie.test import given, strategy
from hypothesis import settings
import brownie
from brownie_tokens import ERC20
import pytest
from tests.conftest import approx

H = 3600
WEEK = 7 * 86400
DAY = 86400
MAXTIME = 126144000
TOL = 120 / WEEK


@pytest.fixture(scope="module", autouse=True)
def initial_setup(chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, vesting):
    chain.sleep(DAY + 1)
    token.update_mining_parameters()
    for i in range(1, 10):
        token_amount = random.randint(40000, 300000) * 10 ** 18
        setup_account(token_amount, accounts[i], accounts, token, voting_escrow)

    token.set_minter(minter.address, {"from": accounts[0]})
    guild_controller.set_minter(minter.address, {"from": accounts[0]})
    vesting.set_minter(minter.address, {"from": accounts[0]})


def setup_account(amount, account, accounts, token, voting_escrow):
    token.transfer(account, amount, {"from": accounts[0]})
    token.approve(voting_escrow.address, amount * 10, {"from": account})
    voting_escrow.create_lock(amount, chain[-1].timestamp + MAXTIME, {"from": account})


@given(st_type_weight=strategy("uint", min_value=10 ** 17, max_value=10 ** 19))
@settings(max_examples=1)
def test_create_type(guild_controller, gas_token, st_type_weight):
    guild_controller.add_type("Gas MOH", "GASMOH", gas_token.address, st_type_weight)
    with brownie.reverts("Already has gas escrow"):
        guild_controller.add_type("Gas ABC", "GASABC", gas_token.address, st_type_weight)
    # create 4 coins and 4 gas escrow
    for i in range(4):
        create_type(i + 1, guild_controller, st_type_weight)


def create_type(type_id, guild_controller, type_weight):
    token_name = "Coin " + str(type_id)
    token_symbol = "MOH" + str(type_id)
    token_contract = ERC20(token_name, token_symbol, 18)

    token_type_name = "GAS" + token_name
    token_type_symbol = "GAS" + token_symbol
    tx = guild_controller.add_type(token_type_name, token_type_symbol, token_contract.address, type_weight)
    assert guild_controller.gas_addr_escrow(token_contract.address) == tx.events['AddType']['gas_escrow']


def create_guild(accounts, guild_owner, guild_rate, guild_type, Guild, guild_controller):
    guild_controller.create_guild(guild_owner, guild_type, guild_rate, {"from": accounts[0]})
    guild_address = guild_controller.guild_owner_list(guild_owner)
    guild_contract = Guild.at(guild_address)
    guild_contract.update_working_balance(guild_owner, {"from": guild_owner})
    return guild_contract


@given(st_type_weight=strategy("uint", min_value=10 ** 17, max_value=10 ** 19))
@settings(max_examples=5)
def test_guild_sum_per_type_and_total(chain, accounts, token, gas_token, voting_escrow, guild_controller, Guild,
                                      st_type_weight):
    guilds = []
    type_weights = []
    # create type
    for i in range(3):
        create_type(i, guild_controller, st_type_weight)
        type_weights.append(st_type_weight)
    chain.sleep(100)
    chain.mine()
    # create 10 guilds, guild type is random
    for i in range(1, 9):
        balance_before = voting_escrow.balanceOf(accounts[i])
        user_point_epoch = voting_escrow.user_point_epoch(accounts[i])
        slope = voting_escrow.user_point_history(accounts[i], user_point_epoch)['slope']
        guild_type = random.randint(0, 2)
        guild_contract = create_guild(accounts, accounts[i], 10, guild_type, Guild, guild_controller)
        expected_weight = balance_before - slope * ((chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp)
        guilds.append({"contract": guild_contract, "type": guild_type,
                       "weight": expected_weight})

        assert approx(expected_weight, guild_controller.get_guild_weight(guild_contract.address), TOL)

    # check guild weight sums per type
    def guild_weight_per_type(index):
        return sum(guild['weight'] for guild in guilds if guild["type"] == index)

    for idx in range(len(type_weights)):
        guild_weight_sum = guild_weight_per_type(idx)
        assert approx(guild_controller.get_weights_sum_per_type(idx), guild_weight_sum, TOL)

    # check total weight
    total_weight = sum(guild_weight_per_type(idx) * weight for idx, weight in enumerate(type_weights))
    assert approx(guild_controller.get_total_weight(), total_weight, TOL)

    chain.sleep(WEEK)
    # check guild relative weight
    for guild, weight, idx in [(gui["contract"], gui["weight"], gui["type"]) for gui in guilds]:
        guild_controller.checkpoint_guild(guild.address)
        expected = 10 ** 18 * type_weights[idx] * weight // total_weight
        print("expected: ", expected, " actual: ", guild_controller.guild_relative_weight(guild.address))
        assert approx(guild_controller.guild_relative_weight(guild.address), expected, TOL)
