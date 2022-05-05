import pytest

from brownie_tokens import ERC20

YEAR = 365 * 86400
INITIAL_RATE = 121_587_840 * 10 ** 18 / YEAR
INITIAL_COMMUNITY_RELEASE_RATE = 121_587_840
YEAR_1_SUPPLY = INITIAL_COMMUNITY_RELEASE_RATE * 10 ** 18 // YEAR * YEAR
INITIAL_SUPPLY = 727_200_000


def approx(a, b, precision=1e-10):
    if a == b == 0:
        return True
    return 2 * abs(a - b) / (a + b) <= precision


def pack_values(values):
    packed = b"".join(i.to_bytes(1, "big") for i in values)
    padded = packed + bytes(32 - len(values))
    return padded


@pytest.fixture(autouse=True)
def isolation_setup(fn_isolation):
    pass


# helper functions as fixtures


# account aliases
@pytest.fixture(scope="session")
def alice(accounts):
    yield accounts[0]


@pytest.fixture(scope="session")
def bob(accounts):
    yield accounts[1]


@pytest.fixture(scope="session")
def charlie(accounts):
    yield accounts[2]


@pytest.fixture(scope="session")
def receiver(accounts):
    yield accounts.at("0x0000000000000000000000000000000000031337", True)


# core contracts

@pytest.fixture(scope="module")
def token(ERC20VRH, accounts):
    yield ERC20VRH.deploy("Vote Escrowed Token", "VRH", 18, {"from": accounts[0]})


@pytest.fixture(scope="module")
def voting_escrow(VotingEscrow, accounts, token):
    yield VotingEscrow.deploy(
        token, "Voting-escrowed VRH", "veVRH", "veVRH_0.99", {"from": accounts[0]}
    )


@pytest.fixture(scope="module")
def gas_token(ERC20Gas, accounts):
    yield ERC20Gas.deploy("Gas Escrowed Token", "MOH", 18, {"from": accounts[0]})


@pytest.fixture(scope="module")
def gas_escrow_template(GasEscrow, accounts, gas_token):
    yield GasEscrow.deploy({"from": accounts[0]})


@pytest.fixture(scope="module")
def guild_template(Guild, accounts):
    yield Guild.deploy({"from": accounts[0]})


@pytest.fixture(scope="module")
def guild_controller(GuildController, accounts, token, guild_template, gas_escrow_template, voting_escrow):
    yield GuildController.deploy(token, voting_escrow, guild_template, gas_escrow_template,
                                 {"from": accounts[0]})


@pytest.fixture(scope="module")
def vesting(RewardVestingEscrow, accounts):
    yield RewardVestingEscrow.deploy({"from": accounts[0]})


@pytest.fixture(scope="module")
def minter(Minter, accounts, guild_controller, token, vesting):
    yield Minter.deploy(token, guild_controller, vesting, {"from": accounts[0]})


# RewardVestingEscrow fixtures


@pytest.fixture(scope="module")
def start_time(chain):
    yield chain.time() + 1000 + 86400 * 365


@pytest.fixture(scope="module")
def end_time(start_time):
    yield start_time + 100000000


# testing contracts

@pytest.fixture(scope="module")
def coin_a():
    yield ERC20("Coin A", "VRH", 18)


@pytest.fixture(scope="module")
def coin_b():
    yield ERC20("Coin B", "MOH", 18)


# helper functions as fixtures

@pytest.fixture(scope="module")
def theoretical_supply(chain, token):
    def _fn():
        epoch = token.mining_epoch()
        q = 1 / 2 ** 0.25
        S = INITIAL_SUPPLY * 10 ** 18
        if epoch > 0:
            S += int(YEAR_1_SUPPLY * (1 - q ** epoch) / (1 - q))
        S += int(YEAR_1_SUPPLY // YEAR * q ** epoch) * (
                chain[-1].timestamp - token.start_epoch_time()
        )
        return S

    yield _fn
