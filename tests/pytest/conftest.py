from starkware.starknet.business_logic.state.state import BlockInfo
from starkware.starknet.testing.starknet import Starknet, StarknetContract
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.compiler.compile import compile_starknet_files
import logging
from types import SimpleNamespace
import asyncio
import pytest
import dill
import os
import sys
import time
from tests.pytest.shared import str_to_felt, uint
from lib.cairo_contracts.tests.signers import MockSigner


sys.setrecursionlimit(3000)

sys.stdout = sys.stderr

# Create signers that use a private key to sign transaction objects.
DUMMY_PRIVATE = 123456789987654321

CONTRACTS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "contracts")
OZ_CONTRACTS_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "lib", "cairo_contracts", "src")
INITIAL_LORDS_SUPPLY = 500000000 * (10**18)
REALM_MINT_PRICE = 10 * (10**18)

first_token_id = (5042, 0)
second_token_id = (7921, 1)
third_token_id = (0, 13)
fourth_token_id = (232, 3453)
fifth_token_id = (234, 345)
sixth_token_id = (9999, 9999)

initial_user_funds = 1000 * (10**18)

initial_supply = 1000000 * (10**18)
DEFAULT_GAS_PRICE = 100


def compile(path) -> ContractClass:
    here = os.path.abspath(os.path.dirname(__file__))

    return compile_starknet_files(
        files=[path],
        debug_info=True,
        disable_hint_validation=True,
        cairo_path=[CONTRACTS_PATH, OZ_CONTRACTS_PATH, here],
    )


async def create_account(starknet, signer, account_class):
    return await starknet.deploy(
        contract_class=account_class,
        constructor_calldata=[signer.public_key],
    )


def get_block_timestamp(starknet_state):
    return starknet_state.state.block_info.block_timestamp


def set_block_timestamp(starknet_state, timestamp):
    starknet_state.state.block_info = BlockInfo(
        starknet_state.state.block_info.block_number, timestamp, DEFAULT_GAS_PRICE, sequencer_address=None, starknet_version=None
    )


# StarknetContracts contain an immutable reference to StarknetState, which
# means if we want to be able to use StarknetState's `copy` method, we cannot
# rely on StarknetContracts that were created prior to the copy.
# For this reason, we specifically inject a new StarknetState when
# deserializing a contract.
def serialize_contract(contract, abi):
    return dict(
        abi=abi,
        contract_address=contract.contract_address,
        deploy_execution_info=contract.deploy_execution_info,
    )


def unserialize_contract(starknet_state, serialized_contract):
    return StarknetContract(state=starknet_state, **serialized_contract)


@pytest.fixture(scope="session")
def event_loop():
    return asyncio.new_event_loop()


@pytest.fixture(scope="session")
async def starknet() -> Starknet:
    starknet = await Starknet.empty()
    return starknet


async def _build_copyable_deployment(compiled_proxy):
    starknet = await Starknet.empty()

    defs = SimpleNamespace(
        account=compile("lib/cairo_contracts/src/openzeppelin/account/presets/Account.cairo"),
        lords=compile("contracts/settling_game/tokens/Lords_ERC20_Mintable.cairo"),
        resources=compile("contracts/settling_game/tokens/Resources_ERC1155_Mintable_Burnable.cairo"),
    )

    signers = dict(admin=MockSigner(83745982347), arbiter=MockSigner(7891011), user1=MockSigner(897654321))

    accounts = SimpleNamespace(
        **{name: (await create_account(starknet, signer, defs.account)) for name, signer in signers.items()}
    )

    lords = await proxy_builder(
        compile("contracts/settling_game/proxy/PROXY_Logic.cairo"),
        starknet,
        signers["admin"],
        accounts.admin,
        "contracts/settling_game/tokens/Lords_ERC20_Mintable.cairo",
        [
            str_to_felt("Lords"),
            str_to_felt("LRD"),
            18,
            *uint(initial_supply),
            accounts.admin.contract_address,
            accounts.admin.contract_address,
        ],
    )

    resources = await proxy_builder(
        compile("contracts/settling_game/proxy/PROXY_Logic.cairo"),
        starknet,
        signers["admin"],
        accounts.admin,
        "contracts/settling_game/tokens/Resources_ERC1155_Mintable_Burnable.cairo",
        [1234, accounts.admin.contract_address],
    )

    return SimpleNamespace(
        starknet=starknet,
        signers=signers,
        accounts=accounts,
        serialized_contracts=dict(
            admin=serialize_contract(accounts.admin, defs.account.abi),
            lords=serialize_contract(lords, defs.lords.abi),
            resources=serialize_contract(resources, defs.resources.abi),
            user1=serialize_contract(accounts.user1, defs.account.abi),
        ),
        addresses=SimpleNamespace(
            admin=accounts.admin.contract_address,
            lords=lords.contract_address,
            resources=resources.contract_address,
            user1=accounts.user1.contract_address,
        ),
    )


@pytest.fixture(scope="session")
async def copyable_deployment(request, compiled_proxy):
    CACHE_KEY = "deployment"
    val = request.config.cache.get(CACHE_KEY, None)
    if val is None:
        val = await _build_copyable_deployment(compiled_proxy)
        res = dill.dumps(val).decode("cp437")
        request.config.cache.set(CACHE_KEY, res)
    else:
        val = dill.loads(val.encode("cp437"))
    return val


@pytest.fixture(scope="session")
async def ctx_factory(copyable_deployment):
    serialized_contracts = copyable_deployment.serialized_contracts
    signers = copyable_deployment.signers

    def make():
        starknet_state = copyable_deployment.starknet.state.copy()

        contracts = {
            name: unserialize_contract(starknet_state, serialized_contract)
            for name, serialized_contract in serialized_contracts.items()
        }

        async def execute(account_name, contract_address, selector_name, calldata):
            return await signers[account_name].send_transaction(
                contracts[account_name],
                contract_address,
                selector_name,
                calldata,
            )

        def advance_clock(num_seconds):
            set_block_timestamp(starknet_state, get_block_timestamp(starknet_state) + num_seconds)

        return SimpleNamespace(
            starknet=Starknet(starknet_state),
            advance_clock=advance_clock,
            signers=signers,
            execute=execute,
            **contracts,
        )

    return make


@pytest.fixture(scope="session")
def compiled_account():
    return compile("lib/cairo_contracts/src/openzeppelin/account/presets/Account.cairo")


@pytest.fixture(scope='session')
async def account_factory(request, compiled_account):
    num_signers = request.param.get("num_signers", "1")
    starknet = await Starknet.empty()
    accounts = []
    signers = []

    print(f'Deploying {num_signers} accounts...')
    for i in range(num_signers):
        signer = MockSigner(DUMMY_PRIVATE + i)
        signers.append(signer)
        account = await starknet.deploy(contract_class=compiled_account, constructor_calldata=[signer.public_key])
        accounts.append(account)

        print(f'Account {i} is: {hex(account.contract_address)}')

    return starknet, accounts, signers


###########################
# COMBAT specific fixtures
###########################


@pytest.fixture(scope="module")
async def l06_combat(starknet, xoroshiro) -> StarknetContract:
    contract = compile("contracts/settling_game/L06_Combat.cairo")
    combat_module = await starknet.deploy(contract_class=contract)
    return combat_module


@pytest.fixture(scope="module")
async def l06_combat_tests(starknet, xoroshiro) -> StarknetContract:
    contract = compile("tests/pytest/settling_game/L06_Combat_tests.cairo")
    # a quirk of the testing framework, even though the L06_Combat_tests contract
    # doesn't have a constructor, it somehow calls (I guess) the constructor of
    # L06_Combat because it imports from it; hence when calling deploy, we need
    # to pass proper constructor_calldata
    return await starknet.deploy(contract_class=contract, constructor_calldata=[])


@pytest.fixture(scope="module")
async def utils_general_tests(starknet) -> StarknetContract:
    contract = compile("tests/pytest/settling_game/utils/general_tests.cairo")
    return await starknet.deploy(contract_class=contract)


###########################
# DESIEGE specific fixtures
###########################

# StarknetContracts contain an immutable reference to StarknetState, which
# means if we want to be able to use StarknetState's `copy` method, we cannot
# rely on StarknetContracts that were created prior to the copy.
# For that reason, we avoid returning any StarknetContracts in this "copyable"
# deployment:
async def _build_copyable_deployment_desiege():
    starknet = await Starknet.empty()

    defs = SimpleNamespace(
        account=compile("lib/cairo_contracts/src/openzeppelin/account/presets/Account.cairo"),
    )

    signers = dict(
        admin=MockSigner(83745982347),
        player1=MockSigner(233294204),
        player2=MockSigner(233294206),
        player3=MockSigner(233294208),
    )

    accounts = SimpleNamespace(
        **{name: (await create_account(starknet, signer, defs.account)) for name, signer in signers.items()}
    )

    return SimpleNamespace(
        starknet=starknet,
        signers=signers,
        serialized_contracts=dict(
            admin=serialize_contract(accounts.admin, defs.account.abi),
            player1=serialize_contract(accounts.player1, defs.account.abi),
            player2=serialize_contract(accounts.player2, defs.account.abi),
            player3=serialize_contract(accounts.player3, defs.account.abi),
        ),
    )


@pytest.fixture(scope="session")
async def copyable_deployment_desiege(request):
    CACHE_KEY = "deployment_desiege"
    val = request.config.cache.get(CACHE_KEY, None)
    if val is None:
        val = await _build_copyable_deployment_desiege()
        res = dill.dumps(val).decode("cp437")
        request.config.cache.set(CACHE_KEY, res)
    else:
        val = dill.loads(val.encode("cp437"))
    return val


@pytest.fixture(scope="session")
async def ctx_factory_desiege(copyable_deployment_desiege):
    serialized_contracts = copyable_deployment_desiege.serialized_contracts
    signers = copyable_deployment_desiege.signers

    def make():
        starknet_state = copyable_deployment_desiege.starknet.state.copy()

        contracts = {
            name: unserialize_contract(starknet_state, serialized_contract)
            for name, serialized_contract in serialized_contracts.items()
        }

        async def execute(account_name, contract_address, selector_name, calldata):
            return await signers[account_name].send_transaction(
                contracts[account_name],
                contract_address,
                selector_name,
                calldata,
            )

        return SimpleNamespace(
            starknet=Starknet(starknet_state),
            execute=execute,
            **contracts,
        )

    return make


###########################
# GAME specific fixtures
###########################


@pytest.fixture(scope="session")
def compiled_proxy():
    return compile("contracts/proxy/PROXY_Logic.cairo")


async def deploy_contract(starknet, contract, calldata):
    print(contract)
    return await starknet.deploy(
        source=contract,
        constructor_calldata=calldata,
    )


async def proxy_builder(compiled_proxy, starknet, signer, account, contract, calldata):

    implementation = await deploy_contract(starknet, contract, [])

    proxy = await starknet.deploy(
        contract_class=compiled_proxy,
        constructor_calldata=[implementation.contract_address],
    )

    set_proxy = proxy.replace_abi(implementation.abi)

    await signer.send_transaction(
        account=account,
        to=set_proxy.contract_address,
        selector_name='initializer',
        calldata=calldata,
    )

    return set_proxy

@pytest.fixture(scope='session')
async def exchange_token_factory(account_factory, compiled_proxy):
    (starknet, accounts, signers) = account_factory
    admin_key = signers[0]
    admin_account = accounts[0]
    treasury_account = accounts[1]

    set_block_timestamp(starknet.state, round(time.time()))

    proxy_lords = await proxy_builder(
        compiled_proxy,
        starknet,
        admin_key,
        admin_account,
        "contracts/exchange/tokens/Lords_ERC20_Mintable.cairo",
        [
            str_to_felt("Lords"),
            str_to_felt("LRD"),
            18,
            *uint(initial_supply),
            admin_account.contract_address,
            admin_account.contract_address,
        ],
    )

    proxy_resources = await proxy_builder(
        compiled_proxy,
        starknet,
        admin_key,
        admin_account,
        "contracts/exchange/tokens/Resources_ERC1155_Mintable_Burnable.cairo",
        [1234, admin_account.contract_address],
    )

    return (starknet, admin_key, admin_account, treasury_account, accounts, signers, proxy_lords, proxy_resources)