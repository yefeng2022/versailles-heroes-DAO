import brownie
from tests.conftest import approx

from brownie.test import given, strategy
from hypothesis import settings
import pytest

H = 3600
DAY = 86400
WEEK = 7 * DAY
MONTH = 4 * WEEK
YEAR = 365 * 86400
MAXTIME = 126144000
TOL = 120 / WEEK
INITIAL_RATE = 121_587_840 * 10 ** 18 / YEAR


@pytest.fixture(scope="module", autouse=True)
def initial_setup(web3, chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, reward_vesting):
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


def test_vesting(chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, reward_vesting, Guild):
    '''
                                  1 vest epoch                  2 vest epoch
                                    |                               |
    |_______|_______|_______|_______|_______|_______|_______|_______|_______|_______|_______|_______|
      1     2       3       4       5       6       7       8       9      10      11      12      13
    1. create_guild
    2. start_mining
    3. first mint and first check vesting claimable token
    5. first vesting epoch start point
    6. check vesting claimable token and second mint
    9. second vesting epoch start point and second check vesting claimable token
    10. third mint check 1 vest epoch and 2 vest epoch
    other skip no checkpoint
    _ mean 1 day
    |_______| mean 1 week
    '''
    alice = accounts[0]
    # 1 creating guild
    create_guild(chain, guild_controller, gas_token, alice, Guild)
    # advance to 2
    chain.sleep((chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp)
    chain.mine()
    # advance to 3 and first check vesting claimable token
    chain.sleep(WEEK)
    chain.mine()
    minter.mint({"from": alice})
    time_3 = chain[-1].timestamp
    print_time(chain[-1].timestamp)
    # check alice vesting amount
    actual_alice_1_epoch_vesting_amount = reward_vesting.user_vesting_history(alice, 1)['amount']
    expected_alice_1_epoch_vesting_amount = token.rate() * WEEK * 0.7
    assert approx(actual_alice_1_epoch_vesting_amount, expected_alice_1_epoch_vesting_amount, TOL)
    # advance to 5, advance to new vesting epoch
    sleep_time = (chain[-1].timestamp // MONTH + 1) * MONTH - chain[-1].timestamp
    chain.sleep(sleep_time)
    chain.mine()
    # advance to 6,
    chain.sleep(WEEK)
    chain.mine()
    # check vesting claimable amount at 6
    vesting_claimable_token = reward_vesting.get_claimable_tokens(alice)
    alice_vesting_slope_5 = reward_vesting.user_vesting_history(alice, 1)['slope']
    assert approx(alice_vesting_slope_5 * WEEK, vesting_claimable_token, TOL)
    # mint at 6
    tx = minter.mint({"from": alice})
    time_6 = chain[-1].timestamp
    print(tx.events)
    chain.sleep(1)
    chain.mine()
    # check vesting claimable token at 6
    alice_vesting_amount_2_epoch = reward_vesting.user_vesting_history(alice, 2)['amount']
    alice_vesting_slope_9 = reward_vesting.user_vesting_history(alice, 2)['slope']
    expect_token_vesting_mintable = token.rate() * (time_6 - time_3) * 0.7
    assert approx(alice_vesting_amount_2_epoch, expect_token_vesting_mintable, TOL)
    # check minted amount at 6
    token_release_immediate_from_3_6 = token.rate() * (time_6 - time_3) * 0.3
    expect_minted = alice_vesting_slope_5 * WEEK + token_release_immediate_from_3_6
    actual_minted = tx.events['Minted']['minted']
    assert approx(actual_minted, expect_minted, TOL)
    # advance to 10
    chain.sleep((chain[-1].timestamp // MONTH + 1) * MONTH - chain[-1].timestamp)
    chain.mine()
    chain.sleep(WEEK)
    chain.mine()
    # check vesting claimable token at 10
    expect_vesting_claimable_token_10 = alice_vesting_slope_5 * MONTH + alice_vesting_slope_9 * WEEK
    actual_vesting_claimable_token_10 = reward_vesting.get_claimable_tokens(alice)
    assert approx(actual_vesting_claimable_token_10, expect_vesting_claimable_token_10, TOL)
    tx = minter.mint({"from": alice})
    # TODO: WIP
    print(tx.events)
    '''
    check vesting clear after 168 days. 
    |_______|_______|_______|_______|_______|_______|_______|_______|_______|_______|_______|_______|
start       1       2       3       4       5       6       7 |     8 |     9      10      11      12
                                                              A       B
    |_______| vesting epoch 28 days
    User will mint every epoch one time  
    1: 1st epoch vesting will be 0 at mint point A
    2: 2nd epoch vesting will be 0 at mint point B
    '''
    for i in range(6):
        # advance to B
        chain.sleep((chain[-1].timestamp // MONTH + 1) * MONTH - chain[-1].timestamp)
        chain.mine()
        chain.sleep(WEEK)
        chain.mine()
        tx = minter.mint({"from": alice})
        print(tx.events)

    actual_epoch_1_remain_amount = reward_vesting.user_vesting_history(alice, 1)['amount']
    actual_epoch_2_remain_amount = reward_vesting.user_vesting_history(alice, 2)['amount']
    # vesting finished after 168 days
    assert actual_epoch_1_remain_amount == 0
    assert actual_epoch_2_remain_amount == 0


def test_skip_one_epoch_vesting(chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, reward_vesting,
                                Guild):
    '''
    check skip 2nd vesting epoch and will accumulate rewards to 3nd vesting epoch
                                  1 vest epoch                  2 vest epoch                     3rd vest epoch
                                    |                               |                               |
    |_______|_______|_______|_______|_______|_______|_______|_______|_______|_______|_______|_______|
      1     2       3       4       5       6       7       8       9      10      11      12      13
    |_______| WEEK

    '''
    alice = accounts[0]
    elapsed_time = 0
    # 1 creating guild
    create_guild(chain, guild_controller, gas_token, alice, Guild)
    # advance to 2 start mining
    sleep_time = (chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp
    chain.sleep(sleep_time)
    chain.mine()
    # advance to 3
    chain.sleep(WEEK)
    chain.mine()
    tx = minter.mint({"from": alice})
    print(tx.events)
    # advance to 10
    sleep_time = (chain[-1].timestamp // MONTH + 1) * MONTH - chain[-1].timestamp
    chain.sleep(sleep_time)
    elapsed_time += sleep_time
    chain.mine()
    chain.sleep(4 * WEEK)
    elapsed_time += 4 * WEEK
    chain.mine()
    chain.sleep(WEEK)
    elapsed_time += WEEK
    chain.mine()
    tx = minter.mint({"from": alice})
    print(tx.events)
    mintable_token = INITIAL_RATE * elapsed_time
    expected_vesting_token = mintable_token * 0.7
    actual_vesting_token = reward_vesting.user_vesting_history(alice, 2)['amount']
    assert approx(actual_vesting_token, expected_vesting_token, TOL)


@given(st_duration=strategy("uint256", min_value=WEEK, max_value=3 * WEEK))
@settings(max_examples=5)
def test_mint_twice_in_epoch(chain, accounts, token, gas_token, voting_escrow, guild_controller, minter, reward_vesting,
                             Guild, st_duration):
    '''
    test mint twice in epoch and will accumulate rewards
                                  1 vest epoch                  2 vest epoch
                                    |                               |
    |_______|_______|_______|_______|_______|_______|_______|_______|_______|___
      1     2       3       4       5       6       7       8       9      10
    |_______| WEEK
    3: 1st mint
    6: 2nd mint
    7: 3rd mint
    '''
    alice = accounts[0]
    elapsed_time = 0
    # 1 creating guild
    create_guild(chain, guild_controller, gas_token, alice, Guild)
    # advance to 2 start mining
    sleep_time = (chain[-1].timestamp // WEEK + 1) * WEEK - chain[-1].timestamp
    chain.sleep(sleep_time)
    chain.mine()
    # advance to 3
    chain.sleep(WEEK)
    chain.mine()
    minter.mint({"from": alice})
    # advance to 6 and mint
    sleep_time = (chain[-1].timestamp // MONTH + 1) * MONTH - chain[-1].timestamp
    chain.sleep(sleep_time)
    elapsed_time += sleep_time
    chain.mine()
    chain.sleep(WEEK)
    elapsed_time += WEEK
    chain.mine()
    minter.mint({"from": alice})
    # get vesting token of
    vesting_token_at_9_mint_6 = reward_vesting.user_vesting_history(alice, 2)['amount']
    # advance to 7 and mint
    chain.sleep(st_duration)
    chain.mine()
    minter.mint({"from": alice})
    vesting_token_at_9_mint_7 = reward_vesting.user_vesting_history(alice, 2)['amount']
    expect_increased_vesting_amount = INITIAL_RATE * st_duration * 0.7
    assert approx(vesting_token_at_9_mint_7 - vesting_token_at_9_mint_6, expect_increased_vesting_amount, TOL)


def print_time(unix_time):
    from datetime import datetime
    print(datetime.utcfromtimestamp(unix_time).strftime('%Y-%m-%d %H:%M:%S'))


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
