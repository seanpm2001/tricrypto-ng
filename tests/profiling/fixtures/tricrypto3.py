import boa
import pytest

from tests.conftest import INITIAL_PRICES
from tests.utils.tokens import mint_for_testing


@pytest.fixture(scope="module")
def init_params():
    ma_time = 866  # 600 / ln(2)

    return {
        "A": 135 * 3**3 * 10000,
        "gamma": int(7e-5 * 1e18),
        "mid_fee": int(4e-4 * 1e10),
        "out_fee": int(4e-3 * 1e10),
        "allowed_extra_profit": 2 * 10**12,
        "fee_gamma": int(0.01 * 1e18),
        "adjustment_step": int(0.0015 * 1e18),
        "admin_fee": 0,
        "ma_time": ma_time,
    }


@pytest.fixture(scope="module")
def math3(deployer):
    with boa.env.prank(deployer):
        return boa.load(
            "contracts/CurveCryptoMathOptimized3.vy",
            name="TricryptoMathOptimized",
        )


def _compiled_swap(coins, tricrypto_math):

    path = "contracts/CurveTricryptoOptimized.vy"

    with open(path, "r") as f:
        source = f.read()
        source = source.replace(
            "0x0000000000000000000000000000000000000000",
            tricrypto_math.address,
        )

        source = source.replace(
            "0x0000000000000000000000000000000000000010", coins[0].address
        )
        source = source.replace(
            "0x0000000000000000000000000000000000000011", coins[1].address
        )
        source = source.replace(
            "0x0000000000000000000000000000000000000012", coins[2].address
        )

        source = source.replace(
            "1,#0", str(10 ** (18 - coins[0].decimals())) + ","
        )
        source = source.replace(
            "1,#1", str(10 ** (18 - coins[1].decimals())) + ","
        )
        source = source.replace(
            "1,#2", str(10 ** (18 - coins[2].decimals())) + ","
        )
        return source


def _crypto_swap(compiled_swap, owner, fee_receiver, init_params, deployer):

    with boa.env.prank(deployer):
        swap = boa.loads(
            compiled_swap,
            owner,
            fee_receiver,
            init_params["A"],
            init_params["gamma"],
            init_params["mid_fee"],
            init_params["out_fee"],
            init_params["allowed_extra_profit"],
            init_params["fee_gamma"],
            init_params["adjustment_step"],
            init_params["admin_fee"],
            init_params["ma_time"],
            INITIAL_PRICES,
            name="TricryptoSwapOptimized",
        )

    return swap


@pytest.fixture(scope="module")
def swap3_empty(owner, fee_receiver, init_params, math3, coins, deployer):
    source = _compiled_swap(coins, math3)
    return _crypto_swap(source, owner, fee_receiver, init_params, deployer)


@pytest.fixture(scope="module")
def views3(deployer, math3, swap3_empty):
    with boa.env.prank(deployer):
        return boa.load(
            "contracts/CurveCryptoViews3Optimized.vy",
            math3,
            swap3_empty,
            name="TricryptoViewsOptimized",
        )


def _crypto_swap_with_deposit(coins, user, tricrypto_swap):
    # add 1M of each token to the pool
    quantities = [
        10**6 * 10**36 // p for p in [10**18] + INITIAL_PRICES
    ]  # $3M worth

    for coin, quantity in zip(coins, quantities):
        # mint coins for user:
        mint_for_testing(coin, user, quantity)
        assert coin.balanceOf(user) == quantity

        # approve crypto_swap to trade coin for user:
        with boa.env.prank(user):
            coin.approve(tricrypto_swap, 2**256 - 1)

    # Very first deposit
    with boa.env.prank(user):
        tricrypto_swap.add_liquidity(quantities, 0)

    return tricrypto_swap


@pytest.fixture(scope="module")
def swap3(swap3_empty, coins, user):
    yield _crypto_swap_with_deposit(coins, user, swap3_empty)
