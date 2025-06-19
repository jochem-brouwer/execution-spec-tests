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
    code = (
        # Copy CALLDATA to memory
        Op.CALLDATACOPY(destoffset=Op.PUSH0, offset=Op.PUSH0, size=Op.CALLDATASIZE)
        # Hash this for the initcode salt (this will be SLOADed to retrieve the actual salt)
        + Op.SHA3(offset=Op.PUSH0, size=Op.CALLDATASIZE)
        + Op.DUP1
        + Op.SLOAD()
        #
        + Op.CREATE2(value=Op.CALLVALUE, offset=Op.PUSH0, size=Op.CALLDATASIZE, salt=Op.DUP1)
        # If ISZERO jump to PC 0 (is not JUMPDEST so invalidates the tx)
        + Op.JUMPI(pc=Op.PUSH0, condition=Op.ISZERO())
        # Add one to salt
        + Op.PUSH1(1)
        + Op.ADD
        # Swap value / key
        + Op.SWAP1
        + Op.SSTORE
    )

    setup_contract = Initcode(deploy_code=code)
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

    runtime_code = (
        (
            Op.JUMP(Op.SUB(Op.CODESIZE, Op.PUSH1(1)))
            .__bytes__()
            .rjust(12, Op.JUMPDEST.__bytes__())
            .rjust(32, b"\x00")
        )
        + Op.ADDRESS
        + Op.OR
    )

    initcode = Op.MSTORE(Op.PUSH0, Op.PUSH32(runtime_code.__bytes__())) + Op.MSTORE(
        Op.PUSH1(32), Op.PUSH32(bytes([0x5B] * 32))
    )

    deploy_contract_1 = Transaction(
        gas_limit=30_000_000, to=deploy_tx.created_contract, sender=sender, data=initcode, nonce=1
    )

    deploy_contract_2 = Transaction(
        gas_limit=30_000_000, to=deploy_tx.created_contract, sender=sender, data=initcode, nonce=1
    )

    post = {}

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=[
            Block(txs=[deploy_tx]),
            Block(txs=[deploy_contract_1]),
            Block(txs=[deploy_contract_2]),
        ],
    )
    # state_test(
    #    env=env,
    #    pre=pre,
    #    post=post,
    #    tx=attack_tx,
    # )


@pytest.mark.valid_from("Cancun")
def test_create_factory(
    blockchain_test: BlockchainTestFiller,
    pre: Alloc,
    fork: Fork,
):
    """
    Creates a tower of contracts which SSTORE values inside this contract.
    Consumes the block gas limit.
    """
    code = (
        Op.CALLDATACOPY(dest_offset=Op.PUSH0, offset=Op.PUSH0, size=Op.CALLDATASIZE)
        + Op.CREATE(value=Op.CALLVALUE, offset=Op.PUSH0, size=Op.CALLDATASIZE)
        + Op.ISZERO
        + Op.PUSH0
        + Op.JUMPI
    )

    setup_contract = Initcode(deploy_code=code)
    env = Environment(gas_limit=100_000_000)

    sender = pre.fund_eoa()

    deploy_tx = Transaction(
        to=None,
        data=setup_contract,
        gas_limit=1_000_000,
        type=0,
        protected=False,
        gas_price=100_000_000_000,
    )

    # 0x36d466250593febc713b9208146a4331865eb00a
    # {
    #    nonce: "0x0",
    #    gasPrice: "0x174876e800",
    #    gasLimit: "0xf4240",
    #    value: "0x0",
    #    data: "0x61000b600081600b8239f3365f5f37365f34f0155f57",
    #    v: 27,
    #    s: 1337,
    #    r: 1337,
    # }

    print(deploy_tx.sender)

    initcode = Op.RETURN(Op.PUSH0, Op.PUSH1(10))

    deploy_contract_1 = Transaction(
        gas_limit=30_000_000, to=deploy_tx.created_contract, sender=sender, data=initcode, nonce=1
    )

    post = {}

    blockchain_test(
        genesis_environment=env,
        pre=pre,
        post=post,
        blocks=[
            Block(txs=[deploy_tx]),
            Block(txs=[deploy_contract_1]),
        ],
    )
