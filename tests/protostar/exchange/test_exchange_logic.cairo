%lang starknet
from starkware.cairo.common.uint256 import Uint256, uint256_add, uint256_mul
from starkware.cairo.common.math_cmp import is_nn, is_le
from starkware.cairo.common.math import unsigned_div_rem, signed_div_rem
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import TRUE, FALSE
from starkware.starknet.common.syscalls import get_block_timestamp

@contract_interface
namespace ProxyInterface:
    func initializer(address_of_controller : felt, proxy_admin : felt):
    end
end

@contract_interface
namespace ILords:
    func initializer(
        name : felt,
        symbol : felt,
        decimals : felt,
        initial_supply : Uint256,
        recipient : felt,
        proxy_admin : felt,
    ):
    end
    func approve(spender : felt, amount : Uint256):
    end
end

@contract_interface
namespace IResources:
    func initializer(name : felt, symbol : felt):
    end
    func mintBatch(
        to : felt, ids_len : felt, ids : Uint256*, amounts_len : felt, amounts : Uint256*, data_len : felt, data : felt*
    ):
    end

    func setApprovalForAll(operator : felt, approved : felt):
    end
end

@contract_interface
namespace IAMM:
    func initializer(
        currency_address_ : felt,
        token_address_ : felt,
        lp_fee_thousands_ : Uint256,
        royalty_fee_thousands_ : Uint256,
        royalty_fee_address_ : felt,
        proxy_admin : felt,
    ):
    end
    func initial_liquidity(
        currency_amounts_len : felt,
        currency_amounts : Uint256*,
        token_ids_len : felt,
        token_ids : Uint256*,
        token_amounts_len : felt,
        token_amounts : Uint256*,
    ):
    end
    func get_all_sell_price(
        token_ids_len : felt,
        token_ids : Uint256*,
        token_amounts_len : felt,
        token_amounts : Uint256*,
    ) -> (sell_value_len : felt, sell_value : Uint256*):
    end
    func get_all_buy_price(
        token_ids_len : felt,
        token_ids : Uint256*,
        token_amounts_len : felt,
        token_amounts : Uint256*,
    ) -> (sell_value_len : felt, sell_value : Uint256*):
    end
    func buy_tokens(
        max_currency_amount : Uint256,
        token_ids_len : felt,
        token_ids : Uint256*,
        token_amounts_len : felt,
        token_amounts : Uint256*,
        deadline : felt
    ):
    end
end

@external
func __setup__{syscall_ptr : felt*, range_check_ptr}():
    alloc_locals

    local account

    local lords_class_hash
    local resources_class_hash

    local proxy_lords
    local proxy_resources

    local ERC1155_AMM_class_hash
    local proxy_ERC1155_AMM

    %{ 
        print("account")
        context.account = deploy_contract("./lib/cairo_contracts/src/openzeppelin/account/presets/Account.cairo", [123]).contract_address
        ids.account = context.account
        print("lords")
        context.lords_class_hash = declare("./contracts/exchange/tokens/Lords_ERC20_Mintable.cairo").class_hash
        context.proxy_lords = deploy_contract("./contracts/proxy/PROXY_Logic.cairo", [context.lords_class_hash]).contract_address
        ids.proxy_lords = context.proxy_lords

        print("resources")
        context.resources_class_hash = declare("./contracts/exchange/tokens/Resources_ERC1155_Mintable_Burnable.cairo").class_hash
        context.proxy_resources = deploy_contract("./contracts/proxy/PROXY_Logic.cairo", [context.resources_class_hash]).contract_address
        ids.proxy_resources = context.proxy_resources

        print("AMM")
        context.ERC1155_AMM_class_hash = declare("./contracts/exchange/Exchange_ERC20_1155.cairo").class_hash
        context.proxy_ERC1155_AMM = deploy_contract("./contracts/proxy/PROXY_Logic.cairo", [context.ERC1155_AMM_class_hash]).contract_address
        ids.proxy_ERC1155_AMM = context.proxy_ERC1155_AMM
    %}

    ILords.initializer(
        proxy_lords, 
        1234, 
        1234, 
        18, 
        Uint256(5000000000000000000000, 0), 
        account, 
        account
    )
    IResources.initializer(proxy_resources, 1234, 123)
    IAMM.initializer(
        proxy_ERC1155_AMM,
        proxy_lords,
        proxy_resources,
        Uint256(100, 0),
        Uint256(100, 0),
        account,
        account,
    )

    let (resource_ids: Uint256*) = alloc()
    assert resource_ids[0] = Uint256(1,0) 
    assert resource_ids[1] = Uint256(2,0)
    assert resource_ids[2] = Uint256(3,0)
    assert resource_ids[3] = Uint256(4,0)
    assert resource_ids[4] = Uint256(5,0)
    assert resource_ids[5] = Uint256(6,0)
    assert resource_ids[6] = Uint256(7,0)
    assert resource_ids[7] = Uint256(8,0)
    assert resource_ids[8] = Uint256(9,0)
    assert resource_ids[9] = Uint256(10,0)

    let (resource_amounts: Uint256*) = alloc()
    assert resource_amounts[0] = Uint256(500 * 10 ** 18, 0)
    assert resource_amounts[1] = Uint256(500 * 10 ** 18, 0)
    assert resource_amounts[2] = Uint256(500 * 10 ** 18, 0)
    assert resource_amounts[3] = Uint256(500 * 10 ** 18, 0)
    assert resource_amounts[4] = Uint256(500 * 10 ** 18, 0)
    assert resource_amounts[5] = Uint256(500 * 10 ** 18, 0)
    assert resource_amounts[6] = Uint256(500 * 10 ** 18, 0)
    assert resource_amounts[7] = Uint256(500 * 10 ** 18, 0)
    assert resource_amounts[8] = Uint256(500 * 10 ** 18, 0)
    assert resource_amounts[9] = Uint256(500 * 10 ** 18, 0)

    let (data : felt*) = alloc()
    assert data[0] = 0

    %{ 
        stop_prank_callable = start_prank(ids.account, target_contract_address=ids.proxy_resources)
    %}

    IResources.mintBatch(
        proxy_resources, 
        account, 
        10, 
        resource_ids, 
        10, 
        resource_amounts,
        1,
        data
    )

    %{ stop_prank_callable() %}

    return ()
end

func initial_liq{syscall_ptr: felt*, range_check_ptr}(
    currency_len : felt, 
    currency_amounts : Uint256*,
    tokens_len : felt,
    token_ids : Uint256*,
    token_amounts_len : felt,
    token_amounts : Uint256*
):
    alloc_locals

    local account
    local proxy_lords
    local proxy_resources
    local proxy_ERC1155_AMM
    %{ 
        ids.account = context.account
        ids.proxy_lords = context.proxy_lords
        ids.proxy_resources = context.proxy_resources
        ids.proxy_ERC1155_AMM = context.proxy_ERC1155_AMM
    %}

    let (sum_currency_amount, _) = uint256_add([currency_amounts],[currency_amounts])

    %{ stop_prank_callable = start_prank(ids.account, target_contract_address=ids.proxy_lords) %}
    ILords.approve(proxy_lords, proxy_ERC1155_AMM, sum_currency_amount)
    %{ stop_prank_callable() %}
    %{ stop_prank_callable = start_prank(ids.account, target_contract_address=ids.proxy_resources) %}
    IResources.setApprovalForAll(proxy_resources, proxy_ERC1155_AMM, TRUE)
    %{ stop_prank_callable() %}
    %{ stop_prank_callable = start_prank(ids.account, target_contract_address=ids.proxy_ERC1155_AMM) %}
    IAMM.initial_liquidity(proxy_ERC1155_AMM, currency_len, currency_amounts, tokens_len, token_ids, tokens_len, token_amounts)
    %{ stop_prank_callable() %}

    return ()
end

func buy_and_check{syscall_ptr: felt*, range_check_ptr}(
    tokens_len : felt,
    token_ids : Uint256*
):

    return ()
end


@external
func test_buy_price{syscall_ptr: felt*, range_check_ptr}():
    alloc_locals

    local account
    local proxy_lords
    local proxy_resources
    local proxy_ERC1155_AMM
    %{ 
        ids.account = context.account
        ids.proxy_lords = context.proxy_lords
        ids.proxy_resources = context.proxy_resources
        ids.proxy_ERC1155_AMM = context.proxy_ERC1155_AMM
    %}

    let currency_reserve = Uint256(10000, 0)
    let token_reserve = Uint256(5000, 0)
    let token_id = Uint256(2, 0)
    let token_id2 = Uint256(4, 0)

    let (currency_amounts: Uint256*) = alloc()
    assert currency_amounts[0] = currency_reserve
    assert currency_amounts[1] = currency_reserve

    let (token_ids: Uint256*) = alloc()
    assert token_ids[0] = token_id
    assert token_ids[1] = token_id2

    let (token_amounts: Uint256*) = alloc()
    assert token_amounts[0] = token_reserve
    assert token_amounts[1] = token_reserve

    initial_liq(2, currency_amounts, 2, token_ids, 2, token_amounts)

    # await buy_and_check([token_id], [100], [227])

    let token_to_buy_amount = Uint256(100, 0)
    let expected_price = Uint256(227, 0)
    let max_currency_val = 259

    let max_currency = Uint256(max_currency_val,0)

    %{ stop_prank_callable = start_prank(ids.account, target_contract_address=ids.proxy_lords) %}
    ILords.approve(proxy_lords, proxy_ERC1155_AMM, max_currency)
    %{ stop_prank_callable() %}

    let (buy_token_ids: Uint256*) = alloc()
    assert buy_token_ids[0] = token_id

    let (buy_token_amounts: Uint256*) = alloc()
    assert buy_token_amounts[0] = token_to_buy_amount

    let (block_timestamp) = get_block_timestamp()
    %{ print(ids.block_timestamp) %}


    # IAMM.buy_tokens(proxy_ERC1155_AMM, max_currency, 1, buy_token_ids, 1, buy_token_amounts, block_timestamp + 10)

    return ()
end

# TODO:
# finish test_buy_check, current erorr in buy_tokens, use fixed point math
# complete implementation from pytest
