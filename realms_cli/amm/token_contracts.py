from nile.core.declare import declare

from collections import namedtuple
from realms_cli.deployer import logged_deploy
from realms_cli.config import Config, strhex_as_strfelt, safe_load_deployment
from realms_cli.shared import str_to_felt
from realms_cli.caller_invoker import wrapped_send
import time

Contracts = namedtuple('Contracts', 'alias contract_name')

# token tuples
TOKEN_CONTRACT_IMPLEMENTATIONS = [
    Contracts("lords", "Lords_ERC20_Mintable"),
    Contracts("resources", "Resources_ERC1155_Mintable_Burnable"),
]

# Lords
LORDS = str_to_felt("Lords")
LORDS_SYMBOL = str_to_felt("LORDS")
DECIMALS = 18

# Resources
REALMS_RESOURCES = str_to_felt("RealmsResources")

def run(nre):

    config = Config(nre.network)

    # implementations
    for contract in TOKEN_CONTRACT_IMPLEMENTATIONS:
        declare(contract.contract_name, nre.network, contract.alias)

        predeclared_class = nre.get_declaration(contract.alias)

        logged_deploy(
            nre,
            'PROXY_Logic',
            alias='proxy_' + contract.alias,
            arguments=[strhex_as_strfelt(predeclared_class)],
        )

    # testnet slow, so waiting period of time before calling otherwise these fail
    # this should be much faster on mainnet
    print('🕒 Waiting for deploy before invoking')
    time.sleep(120)

    # init proxies
    wrapped_send(
        network=config.nile_network,
        signer_alias=config.USER_ALIAS,
        contract_alias="proxy_lords",
        function="initializer",
        arguments=[
            LORDS,
            LORDS_SYMBOL,
            DECIMALS,
            str(config.INITIAL_LORDS_SUPPLY),
            "0",
            strhex_as_strfelt(config.USER_ADDRESS),
            strhex_as_strfelt(config.USER_ADDRESS),
        ],
    )

    wrapped_send(
        network=config.nile_network,
        signer_alias=config.USER_ALIAS,
        contract_alias="proxy_resources",
        function="initializer",
        arguments=[
            REALMS_RESOURCES,
            strhex_as_strfelt(config.USER_ADDRESS),  # contract_owner
        ],
    )