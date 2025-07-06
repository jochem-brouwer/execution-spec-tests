import math

import pytest

from ethereum_test_forks import Fork
from ethereum_test_tools import (
    Account,
    Address,
    Alloc,
    Block,
    BlockchainTestFiller,
    Bytecode,
    Environment,
    Hash,
    StateTestFiller,
    Transaction,
    While,
    compute_create2_address,
    compute_create_address,
)
from ethereum_test_tools.code.generators import Initcode
from ethereum_test_tools.vm.opcode import Opcodes as Op


@pytest.mark.valid_from("Cancun")
@pytest.mark.parametrize("value_bearing", [True, False])
def test_worst_selfdestruct_existing(
    blockchain_test: BlockchainTestFiller,
    fork: Fork,
    pre: Alloc,
    value_bearing: bool,
):
    """Test running a block with as many SELFDESTRUCTs as possible for existing contracts."""
    env = Environment(gas_limit=100_000_000_000)
    attack_gas_limit = Environment().gas_limit
    pre.fund_address(env.fee_recipient, 1)

    # Template code that will be used to deploy a large number of contracts.
    selfdestructable_contract_addr = pre.deploy_contract(code=Op.SELFDESTRUCT(Op.COINBASE))
    initcode = Op.EXTCODECOPY(
        address=selfdestructable_contract_addr,
        dest_offset=0,
        offset=0,
        size=Op.EXTCODESIZE(selfdestructable_contract_addr),
    ) + Op.RETURN(0, Op.EXTCODESIZE(selfdestructable_contract_addr))
    initcode_address = pre.deploy_contract(code=initcode)

    # Create a factory that deployes a new SELFDESTRUCT contract instance pre-funded depending on
    # the value_bearing parameter. We use CREATE2 so the caller contract can easily reproduce
    # the addresses in a loop for CALLs.
    factory_code = (
        Op.EXTCODECOPY(
            address=initcode_address,
            dest_offset=0,
            offset=0,
            size=Op.EXTCODESIZE(initcode_address),
        )
        + Op.MSTORE(
            0,
            Op.CREATE2(
                value=1 if value_bearing else 0,
                offset=0,
                size=Op.EXTCODESIZE(initcode_address),
                salt=Op.SLOAD(0),
            ),
        )
        + Op.SSTORE(0, Op.ADD(Op.SLOAD(0), 1))
        + Op.RETURN(0, 32)
    )
    factory_address = pre.deploy_contract(code=factory_code, balance=10**18)

    factory_caller_code = Op.CALLDATALOAD(0) + While(
        body=Op.POP(Op.CALL(address=factory_address)),
        condition=Op.PUSH1(1) + Op.SWAP1 + Op.SUB + Op.DUP1 + Op.ISZERO + Op.ISZERO,
    )
    factory_caller_address = pre.deploy_contract(code=factory_caller_code)

    gas_costs = fork.gas_costs()
    intrinsic_gas_cost_calc = fork.transaction_intrinsic_cost_calculator()
    loop_cost = (
        gas_costs.G_KECCAK_256  # KECCAK static cost
        + math.ceil(85 / 32) * gas_costs.G_KECCAK_256_WORD  # KECCAK dynamic cost for CREATE2
        + gas_costs.G_VERY_LOW * 3  # ~MSTOREs+ADDs
        + gas_costs.G_COLD_ACCOUNT_ACCESS  # CALL to self-destructing contract
        + gas_costs.G_SELF_DESTRUCT
        + 30  # ~Gluing opcodes
    )
    num_contracts = (
        # Base available gas = GAS_LIMIT - intrinsic - (out of loop MSTOREs)
        attack_gas_limit - intrinsic_gas_cost_calc() - gas_costs.G_VERY_LOW * 4
    ) // loop_cost

    contracts_deployment_tx = Transaction(
        to=factory_caller_address,
        gas_limit=env.gas_limit,
        gas_price=10**9,
        data=Hash(num_contracts),
        sender=pre.fund_eoa(),
    )

    code = (
        # Setup memory for later CREATE2 address generation loop.
        # 0xFF+[Address(20bytes)]+[seed(32bytes)]+[initcode keccak(32bytes)]
        Op.MSTORE(0, factory_address)
        + Op.MSTORE8(32 - 20 - 1, 0xFF)
        + Op.MSTORE(32, 0)
        + Op.MSTORE(64, initcode.keccak256())
        # Main loop
        + While(
            body=Op.POP(Op.CALL(address=Op.SHA3(32 - 20 - 1, 85)))
            + Op.MSTORE(32, Op.ADD(Op.MLOAD(32), 1)),
            # Stop before we run out of gas for the whole tx execution.
            # The value was found by trial-error rounded to the next 1000 multiple.
            condition=Op.GT(Op.GAS, 12_000),
        )
        + Op.SSTORE(0, 42)  # Done for successful tx execution assertion below.
    )
    assert len(code) <= fork.max_code_size()

    # The 0 storage slot is initialize to avoid creation costs in SSTORE above.
    code_addr = pre.deploy_contract(code=code, storage={0: 1})
    opcode_tx = Transaction(
        to=code_addr,
        gas_limit=attack_gas_limit,
        gas_price=10,
        sender=pre.fund_eoa(),
    )

    post = {
        code_addr: Account(storage={0: 42})  # Check for successful execution.
    }
    deployed_contract_addresses = []
    for i in range(num_contracts):
        deployed_contract_address = compute_create2_address(
            address=factory_address,
            salt=i,
            initcode=initcode,
        )
        post[deployed_contract_address] = Account(nonce=1)
        deployed_contract_addresses.append(deployed_contract_address)

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=[
            Block(txs=[contracts_deployment_tx]),
            Block(txs=[opcode_tx]),
        ],
        exclude_full_post_state_in_output=True,
    )
