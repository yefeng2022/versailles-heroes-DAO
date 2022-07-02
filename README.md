# versailles-heroes-DAO

Vyper contracts used in the Versailles Heroes Governance DAO.

## Overview

Versailles Heroes DAO consists of multiple smart contracts connected by [Aragon](https://github.com/aragon/aragonOS). Interaction with Aragon occurs through a [modified implementation](https://github.com/Versailles-heroes-com/VRH-Aragon-DAO) of the [Aragon Voting App](https://github.com/aragon/aragon-apps/tree/master/apps/voting). Aragon's standard one token, one vote method is replaced with a weighting system based on locking tokens. Versailles Heroes DAO has a token (VRH) which is used for both governance and value accrual.

View the [documentation](https://docs.versaillesheroes.com/) for a more in-depth explanation of how Versailles Heroes DAO works.

## Testing and Development

### Dependencies

- [python3](https://www.python.org/downloads/release/python-3910/) version 3.9.10
- [vyper](https://github.com/vyperlang/vyper) version [0.3.1](https://github.com/vyperlang/vyper/releases/tag/v0.3.1)
- [brownie](https://github.com/iamdefinitelyahuman/brownie) - tested with version [1.18.1](https://github.com/eth-brownie/brownie/releases/tag/v1.14.6)
- [brownie-token-tester](https://github.com/iamdefinitelyahuman/brownie-token-tester) - tested with version [0.3.2](https://github.com/iamdefinitelyahuman/brownie-token-tester/releases/tag/v0.3.2)
- [ganache](https://trufflesuite.com/ganache) - tested with version [2.5.4](https://github.com/trufflesuite/ganache-ui/releases/tag/v2.5.4)

### Setup

To get started, first create and initialize a Python [virtual environment](https://docs.python.org/3/library/venv.html). Next, clone the repo and install the developer dependencies:

```bash
git clone https://github.com/Versailles-heroes-com/versailles-heroes-DAO.git
cd versailles-heroes-DAO
pip install -r requirements.txt
```

### Running the Tests

The test suite is split between [unit](tests/unitary) and [integration](tests/integration) tests. To run the entire suite:

```bash
brownie test
```

To run only the unit tests or integration tests:

```bash
brownie test tests/unitary
brownie test tests/integration
```

## Deployment

See the [deployment documentation](scripts/deployment/README.md) for detailed information on how to deploy Versailles Heroes DAO.

## Audits and Security



## Resources

You may find the following guides useful:

1. [Versailles Heroes DAO Resources](https://docs.versaillesheroes.com/)
2. [How to earn and claim VRH](https://docs.versaillesheroes.com/more../faq#1.-how-is-vrh-mined)
3. [Voting and vote locking on Versailles Heroes DAO](https://docs.versaillesheroes.com/vrh-dao/vote-escrowed-vrh)

## Community

If you have any questions about this project, or wish to engage with us:

- [Telegram](https://t.me/)
- [Twitter](https://twitter.com/)
- [Discord](https://discord.gg/)

## License

This project is licensed under the [MIT](LICENSE) license.
