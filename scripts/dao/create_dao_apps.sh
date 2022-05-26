#!/bin/bash

source env
#dao new --env $DEPLOY_ENV

## create app
dao install $DAO_ADDRESS agent --env $DEPLOY_ENV
dao install $DAO_ADDRESS agent --env $DEPLOY_ENV

dao install $DAO_ADDRESS ownership-voting.open.aragonpm.eth --app-init-args $VOTING_ESCROW 510000000000000000 500000000000000000 3600 2500 10 2500 50000 10 1000 --env $DEPLOY_ENV --ipfs-rpc https://ipfs.infura-ipfs.io:5001/ --ipfs-gateway https://ipfs.infura-ipfs.io/ipfs

dao install $DAO_ADDRESS create-guild-voting.open.aragonpm.eth --app-init-args $VOTING_ESCROW 510000000000000000 500000000000000000 3600 1000000 10 1000000 100000000 10 1000 --env $DEPLOY_ENV --ipfs-rpc https://ipfs.infura-ipfs.io:5001/ --ipfs-gateway https://ipfs.infura-ipfs.io/ipfs

dao apps $DAO_ADDRESS --all --env $DEPLOY_ENV
dao acl view $DAO_ADDRESS --env $DEPLOY_ENV
