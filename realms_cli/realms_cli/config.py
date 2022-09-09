""""
This file hold all high-level config parameters

Use:
from realms_cli.realms_cli.config import Config

... = Config.NILE_NETWORK
"""
from nile import deployments
from nile.core.declare import alias_exists
import os


def safe_load_deployment(alias: str, network: str):
    """Safely loads address from deployments file"""
    try:
        address, _ = next(deployments.load(alias, network))
        print(f"Found deployment for alias {alias}.")
        return address, _
    except StopIteration:
        print(f"Deployment for alias {alias} not found.")
        return None, None


def safe_load_declarations(alias: str, network: str):
    """Safely loads address from deployments file"""
    address, _ = next(deployments.load_class(alias, network), None)
    print(f"Found deployment for alias {alias}.")
    return address


def strhex_as_strfelt(strhex: str):
    """Converts a string in hex format to a string in felt format"""
    if strhex is not None:
        return str(int(strhex, 16))
    else:
        print("strhex address is None.")


class Config:
    def __init__(self, nile_network: str):
        self.nile_network = "127.0.0.1" if nile_network == "localhost" else nile_network

        self.ADMIN_ALIAS = "STARKNET_ADMIN_PRIVATE_KEY"
        self.ADMIN_ADDRESS, _ = safe_load_deployment(
            "account-0", self.nile_network)

        self.INITIAL_LORDS_SUPPLY = 500000000 * (10 ** 18)

        self.USER_ALIAS = "STARKNET_PRIVATE_KEY"
        self.USER_ADDRESS, _ = safe_load_deployment(
            "account-1", self.nile_network)

        self.LORDS_ADDRESS, _ = safe_load_deployment(
            "lords", self.nile_network)
        self.RESOURCES_ADDRESS, _ = safe_load_deployment(
            "resources", self.nile_network)
       
        self.LORDS_PROXY_ADDRESS, _ = safe_load_deployment(
            "proxy_lords", self.nile_network)
        self.RESOURCES_PROXY_ADDRESS, _ = safe_load_deployment(
            "proxy_resources", self.nile_network)

        self.Exchange_ERC20_1155_ADDRESS, _ = safe_load_deployment(
            "Exchange_ERC20_1155", self.nile_network)
        self.Exchange_ERC20_1155_PROXY_ADDRESS, _ = safe_load_deployment(
            "proxy_Exchange_ERC20_1155", self.nile_network)

        self.RESOURCES = [
            "Wood",
            "Stone",
            "Coal",
            "Copper",
            "Obsidian",
            "Silver",
            "Ironwood",
            "ColdIron",
            "Gold",
            "Hartwood",
            "Diamonds",
            "Sapphire",
            "Ruby",
            "DeepCrystal",
            "Ignium",
            "EtherealSilica",
            "TrueIce",
            "TwilightQuartz",
            "AlchemicalSilver",
            "Adamantine",
            "Mithral",
            "Dragonhide",
            # "DesertGlass",
            # "DivineCloth",
            # "CuriousSpre",
            # "UnrefinedOre",
            # "SunkenShekel",
            # "Demonhide",
            "Wheat",
            "Fish"
        ]
