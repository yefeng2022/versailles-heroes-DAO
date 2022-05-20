import brownie

def test_transfer_guild_controller_ownership(accounts, guild_controller):
    alice, bob, carl = accounts[:3]

    assert(guild_controller.admin() == alice)

    with brownie.reverts('dev: admin only'):
        guild_controller.commit_transfer_ownership(bob, {"from": carl})

    # commit ownership
    guild_controller.commit_transfer_ownership(bob, {"from": alice})
    
    assert(guild_controller.future_admin() == bob)

    with brownie.reverts('dev: admin only'):
        guild_controller.apply_transfer_ownership({"from": carl})

    # apply commit
    guild_controller.apply_transfer_ownership({"from": alice})

    assert(guild_controller.admin() == bob)


def test_transfer_create_guild_ownership(accounts, guild_controller):
    alice, bob, carl = accounts[:3]

    assert(guild_controller.create_guild_admin() == alice)

    with brownie.reverts('dev: admin only'):
        guild_controller.commit_transfer_create_guild_ownership(bob, {"from": carl})

    # commit ownership
    guild_controller.commit_transfer_create_guild_ownership(bob, {"from": alice})
    
    assert(guild_controller.future_create_guild_admin() == bob)

    with brownie.reverts('dev: admin only'):
        guild_controller.apply_transfer_create_guild_ownership({"from": carl})

    # apply commit
    guild_controller.apply_transfer_create_guild_ownership({"from": alice})

    assert(guild_controller.create_guild_admin() == bob)

