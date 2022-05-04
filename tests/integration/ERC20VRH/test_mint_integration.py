import brownie
import pytest
from brownie.test import given, strategy

from tests.conftest import YEAR


@pytest.fixture(scope="module", autouse=True)
def initial_setup(chain, token):
    chain.sleep(86401)
    token.update_mining_parameters()


@given(duration=strategy("uint", min_value=86500, max_value=YEAR))
def test_mint(accounts, chain, token, duration):
    token.set_minter(accounts[0], {"from": accounts[0]})
    creation_time = token.start_epoch_time()
    initial_supply = token.totalSupply()
    rate = token.rate()
    chain.sleep(duration)

    amount = (chain.time() - creation_time) * rate
    token.mint(accounts[1], amount, {"from": accounts[0]})

    assert token.balanceOf(accounts[1]) == amount
    assert token.totalSupply() == initial_supply + amount


@given(duration=strategy("uint", min_value=86500, max_value=YEAR))
def test_overmint(accounts, chain, token, duration):
    token.set_minter(accounts[0], {"from": accounts[0]})
    creation_time = token.start_epoch_time()
    rate = token.rate()
    chain.sleep(duration)

    with brownie.reverts("dev: exceeds allowable mint amount"):
        token.mint(accounts[1], (chain.time() - creation_time + 2) * rate, {"from": accounts[0]})