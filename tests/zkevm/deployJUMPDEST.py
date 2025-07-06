import math

import pytest

from ethereum_test_base_types.base_types import Bytes
from ethereum_test_base_types.conversions import BytesConvertible, FixedSizeBytesConvertible
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
    compute_create_address,
)
from ethereum_test_tools import Macros as Om
from ethereum_test_tools.code.generators import Initcode
from ethereum_test_tools.vm.opcode import Opcodes as Op


# 0x983c0d395b635982c3566f986f6d6b4fa3d78b30a7f37d6c548b4ee984a4cb13
def generate_jumpdest(target_size):
    initcode = (
        Op.PUSH32(
            Op.JUMP(Op.SUB(Op.CODESIZE, Op.PUSH1(1)))
            .__bytes__()
            .ljust(12, Op.JUMPDEST.__bytes__())
            .ljust(32, b"\x00")
        )
        + Op.ADDRESS
        + Op.OR
        + Op.PUSH0
        + Op.MSTORE
        + Op.MSTORE(Op.PUSH1(32), Op.PUSH32(Op.JUMPDEST.__bytes__() * 32))
    )

    msize = 64
    current_target = 64
    offset = 32
    current_size = 32

    while msize < target_size:
        next_target = current_target + current_size
        if next_target > target_size:
            current_size -= next_target - target_size
        initcode += Op.MCOPY(current_target, offset, current_size)
        msize = current_target + current_size
        current_target = current_target + current_size
        current_size = current_size * 2

    initcode += Op.RETURN(Op.PUSH0, target_size)
    print(initcode.hex())
    return initcode


generate_jumpdest(0x6000 * 2)


def compute_create2_address(
    address: FixedSizeBytesConvertible, salt: FixedSizeBytesConvertible, initcode: Hash
) -> Address:
    """
    Compute address of the resulting contract created using the `CREATE2`
    opcode.
    """
    hash_bytes = Bytes(b"\xff" + Address(address) + Hash(salt) + Bytes(initcode)).keccak256()
    return Address(hash_bytes[-20:])


print(
    compute_create2_address(
        address="0xe883a4aC7904c5B91fAaec2CECcb236d985FC329",
        salt=9760,
        # initcode="0xbfbe36239a3b4ec60fe1d0abf19c71d302979fd7ccb95e5965ba48ffd46638f4", # 140_000
        initcode="0x8eadfaa0e39b9fa42c45b2bd08a25811f9a53f5e6184863f4693a74cd69978ab",
    )
)

print(compute_create_address(address="0xF07f8D8D3a19Bae6d786d17A7ffC7aE970f4137B", nonce=0))
