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
def test_bytecode_read_bench(
    blockchain_test: BlockchainTestFiller,
    pre: Alloc,
    fork: Fork,
):
    """
    Creates a tower of contracts which SSTORE values inside this contract.
    Consumes the block gas limit.
    """

    sstore_count = 0
    bytecode_size = 0x6000  # fork.max_code_size()  # Bytecode size of contract to deploy.

    # The ADDRESS is stored in the code, which is by MSTORE right aligned
    # To fit this in the code (it is left padded with 0s / STOPs) assert
    # the code is at least 32 bytes
    assert bytecode_size >= 32

    # This code creates different storage tries for every contract
    # sstore_code = Op.SSTORE(Op.GAS, Op.GAS) * sstore_count
    # deposit_code = Op.MSTORE(Op.PUSH0, Op.ADDRESS) + Op.RETURN(0, bytecode_size)
    # initcode = sstore_code + deposit_code
    initcode = Op.MSTORE(1, Op.ADDRESS) + Op.RETURN(Op.PUSH0, bytecode_size)

    setup_memory = Op.CALLDATACOPY(Op.PUSH0, Op.PUSH0, Op.CALLDATASIZE)
    loop = Op.POP(Op.CREATE(Op.PUSH0, Op.PUSH0, Op.CALLDATASIZE))

    attack_contract = (
        setup_memory
        + loop
        + Op.GAS
        + loop
        + Op.GAS
        + Op.SWAP1
        + Op.SUB
        + While(body=loop, condition=Op.GT(Op.GAS, Op.DUP1))
    )

    setup_contract = Initcode(deploy_code=attack_contract)
    env = Environment(gas_limit=100_000_000)

    sender = pre.fund_eoa()

    deploy_tx = Transaction(
        to=None,
        data=setup_contract,
        gas_limit=22_000_000,
        type=0,
        protected=False,
        gas_price=100_000_000_000,
    )
    attack_tx = Transaction(
        gas_limit=22_000_000, to=deploy_tx.created_contract, sender=sender, data=initcode, nonce=1
    )

    post = {}

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=[Block(txs=[deploy_tx]), Block(txs=[attack_tx])],
    )
    # state_test(
    #    env=env,
    #    pre=pre,
    #    post=post,
    #    tx=attack_tx,
    # )
