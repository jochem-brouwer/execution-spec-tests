from ethereum_test_base_types.base_types import Address
from ethereum_test_tools import (
    Account,
    Alloc,
    Block,
    BlockchainTestFiller,
    Bytecode,
    Environment,
    Hash,
    Transaction,
    While,
    compute_create_address,
)
from ethereum_test_tools import Macros as Om
from ethereum_test_tools.vm.opcode import Opcodes as Op

limit = 0x6000

contracts = []
# BIG factory [24 KiB]
# Nonce = 5273 so 5272 contracts
factory = "0x57603B698AFc4983F1201e6718BBFB2e7b2b4fFF"


# SMALL factory [12 KiB]
# Nonce = 6697 so 6696 contracts
factory = "0x2d6d1910F67B4542dB22d8D5cc578E72aAE912eD"

for i in range(5050):
    nonce = i + 1
    contracts.append(compute_create_address(address=factory, nonce=nonce))

# print(contracts[0])
# my_bytes_array = b"\0\1\2"
# print(Om.MSTORE(my_bytes_array).hex())


def start_code(index: int):
    address = contracts[index]
    return Op.STATICCALL(
        gas=Op.GAS,
        address=address,
        args_offset=Op.PUSH0,
        args_size=Op.PUSH0,
        ret_offset=Op.PUSH0,
        ret_size=Op.PUSH0,
    )


def add_code(index: int):
    # "args_size", "ret_offset", "ret_size"
    address = contracts[index]
    return Op.STATICCALL(
        gas=Op.GAS,
        address=address,
        args_offset=Op.PUSH0,
        args_size=Op.PUSH0,
        ret_offset=Op.PUSH0,
        ret_size=Bytecode(),  # Use previous stack item (0 or 1)
    )


def factory_code(index: int):
    code = start_code(index)
    index = index + 1
    codes_targeted = 1

    while index < len(contracts):
        append = add_code(index)
        if len(code) + len(append) <= limit:
            code = code + append
            index += 1
            codes_targeted += 1
        else:
            break

    return [index, codes_targeted, code._bytes_.ljust(limit, b"\x00")]


current_index = 0
while current_index < len(contracts):
    attack_data = factory_code(current_index)
    current_index = attack_data[0]
    print("bytecode", attack_data[2].hex())
    print("current index", attack_data[0])
    print("codes deployed", attack_data[1])
