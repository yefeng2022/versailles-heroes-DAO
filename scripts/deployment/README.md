# versailles-heroes-dao/scripts/deployment

Deployment scripts for the versailles heroes DAO.

## Dependencies

* [Brownie](https://github.com/eth-brownie/brownie)
* [Aragon CLI](https://github.com/aragon/aragon-cli)
* [Ganache](https://github.com/trufflesuite/ganache-cli)

## Process Overview

### 1. Initial Setup

[`deployment_config.py`](deployment_config.py) holds configurable / sensitive values related to the deployment. Before starting, you must set the following variables:

* Modify the `get_live_admin` function to return the primary admin [`Account`](https://eth-brownie.readthedocs.io/en/stable/api-network.html#brownie.network.account.Account) object and four funding admin accounts. See the Brownie [account management](https://eth-brownie.readthedocs.io/en/stable/account-management.html) documentation for information on how to unlock local accounts.

### 2. Deploying the versailles heroes DAO

1. If you haven't already, install [Brownie](https://github.com/eth-brownie/brownie)

    ```bash
    pip install eth-brownie
    ```

2. Verify [`deploy_dao`](deploy_dao.py) by testing in on a forked mainnet:

    ```bash
    brownie run deploy_dao development --network mainnet-fork
    ```

3. Run the first stage of the [`deploy_dao`](deploy_dao.py) script:

    Live deployment this is split into two calls. The first action deploys only `ERC20VRH` and `VotingEscrow`:

    ```bash
    brownie run deploy_dao live_part_one --network mainnet
    ```

    With these contracts deployed, the Aragon DAO setup can begin while the rest of Curve DAO is deployed.

4. Run the second stage of [`deploy_dao`](deploy_dao.py):

    ```bash
    brownie run deploy_dao live_part_two --network mainnet
    ```

    This deploys and links all of the core versailles heroes DAO contracts. A JSON is generated containing the address of each deployed contract. **DO NOT MOVE OR DELETE THIS FILE**. It is required in later deployment stages.

### 3. Deploying the Aragon DAO

1. If you haven't already, install the [Aragon CLI](https://github.com/aragon/aragon-cli):

    ```bash
    npm install --global @aragon/cli
    ```

Aragon: [Custom Deploy](https://hack.aragon.org/docs/guides-custom-deploy)

# Deploy the [Versailles Aragon Voting App](https://github.com/Versailles-heroes-com/versailles-heroes-DAO/blob/master/README.md)

# Deploy Aragon DAO

Read instructions in [Deploy Aragon DAO README](./Deploy_Aragon_DAO_README.md)

Once the DAO is successfully deployed, modify [`deployment_config`](deployment_config.py) so that `ARAGON_AGENT` points to the [Aragon Ownership Agent](https://github.com/aragon/aragon-apps/blob/master/apps/agent/contracts/Agent.sol) deployment.

Deploy subgraphs for Curve Voting App and VotingEscrow

### 4. Transferring Ownership of versailles heroes DAO to Aragon

1. Verify [`transfer_dao_ownership`](transfer_dao_ownership) by testing it on a forked mainnet:

    ```
    brownie run transfer_dao_ownership development --network mainnet-fork
    ```

2. Run the [`transfer_dao_ownership`](transfer_dao_ownership) script:

    If you haven't yet, modify [`deployment_config`](deployment_config.py) so that `ARAGON_AGENT` points to the [Aragon Ownership Agent](https://github.com/aragon/aragon-apps/blob/master/apps/agent/contracts/Agent.sol) deployment address. Then:

    ```bash
    brownie run transfer_dao_ownership live --network mainnet
    ```

    This transfers the ownership of [`GuildController`](../../contracts/GuildController.vy), [`VotingEscrow`](../../contracts/VotingEscrow.vy), [`RewardVestingEscrow`](../../contracts/RewardVestingEscrow.vy) and [`ERC20VRH`](../../contracts/ERC20VRH.vy) from the main admin account to the [Aragon Ownership Agent](https://github.com/aragon/aragon-apps/blob/master/apps/agent/contracts/Agent.sol).
