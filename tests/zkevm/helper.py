import json

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
from ethereum_test_tools.code.generators import Initcode
from ethereum_test_tools.vm.opcode import Opcodes as Op

root_deployer = "0x7e7eeb315827261eedb8e1504b6d806069a1a2ba"
current_root_nonce = 101
to_deploy = 13

limit = 0x6000
targets = 12500

# PREPEND THIS WITH STATICCALL ROOT CONTRACT
children_contracts = []

print(compute_create_address(address=root_deployer, nonce=0).hex())

for nonce in range(current_root_nonce + 1, current_root_nonce + 1 + to_deploy):
    children_contracts.append(compute_create_address(address=root_deployer, nonce=nonce))

print(children_contracts[0].hex(), children_contracts[1].hex())

# BIG factory [24 KiB]
# 9152 contracts NEED: 11489
factory = "0x57603B698AFc4983F1201e6718BBFB2e7b2b4fFF"


# SMALL factory [12 KiB]
# Nonce = 6697 so 6696 contracts
# factory = "0x2d6d1910F67B4542dB22d8D5cc578E72aAE912eD"

TARGET_OPCODE = "EXTCODESIZE"
COPY_BYTE = 0x6000 - 1

if factory == "0x2d6d1910F67B4542dB22d8D5cc578E72aAE912eD":
    COPY_BYTE = 0x3000 - 1


contracts = []
for i in range(targets):
    nonce = i + 1
    contracts.append(compute_create_address(address=factory, nonce=nonce))

# print(contracts[0])
# my_bytes_array = b"\0\1\2"
# print(Om.MSTORE(my_bytes_array).hex())


def start_code(index: int):
    if index == 0 and len(children_contracts) > 0:
        code = Op.STATICCALL(
            gas=Op.GAS,
            address=children_contracts[0],
            args_offset=Op.PUSH0,
            args_size=Op.PUSH0,
            ret_offset=Op.PUSH0,
            ret_size=Op.PUSH0,
        )
        index += 1
        for child_contract in children_contracts[1:]:
            code += Op.STATICCALL(
                gas=Op.GAS,
                address=child_contract,
                args_offset=Op.PUSH0,
                args_size=Op.PUSH0,
                ret_offset=Op.PUSH0,
                ret_size=Bytecode(),  # Use previous stack item (0 or 1)
            )
            index += 1

        if TARGET_OPCODE.find("CALL") == -1:
            code += Op.POP
        if TARGET_OPCODE == "EXTCODECOPY":
            code += Op.PUSH1(1)

        return [code, index]
    else:
        address = contracts[index]
        code = Bytecode()
        if TARGET_OPCODE == "STATICCALL":
            code += Op.STATICCALL(
                gas=Op.GAS,
                address=address,
                args_offset=Op.PUSH0,
                args_size=Op.PUSH0,
                ret_offset=Op.PUSH0,
                ret_size=Op.PUSH0,
            )
        if TARGET_OPCODE == "EXTCODECOPY":
            code += Op.PUSH1(1)
        index += 1
        return [code, index]


def add_code(index: int):
    address = contracts[index]
    if TARGET_OPCODE == "STATICCALL":
        return Op.STATICCALL(
            gas=Op.GAS,
            address=address,
            args_offset=Op.PUSH0,
            args_size=Op.PUSH0,
            ret_offset=Op.PUSH0,
            ret_size=Bytecode(),  # Use previous stack item (0 or 1)
        )
    elif TARGET_OPCODE == "EXTCODECOPY":
        # "address", "dest_offset", "offset", "size"
        return Op.EXTCODECOPY(
            address=address, dest_offset=Op.PUSH0, offset=COPY_BYTE, size=Op.DUP1
        )
    elif TARGET_OPCODE == "EXTCODESIZE":
        return Op.POP(Op.EXTCODESIZE(address=address))
    else:
        raise Exception("unsupported opcode", TARGET_OPCODE)


def factory_code(index: int):
    start = start_code(index)
    code = start[0]
    index = start[1]
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

ctrs = 0

initcodes = []

while current_index < len(contracts):
    attack_data = factory_code(current_index)
    current_index = attack_data[0]
    # print("bytecode", attack_data[2].hex())
    print("current index", attack_data[0])
    print("codes deployed", attack_data[1])
    initcodes.append(Initcode(deploy_code=attack_data[2]).hex())
    ctrs += 1

with open("hex_data.json", "w") as f:
    json.dump(initcodes, f)

print(
    "TARGET ATTACK CONTRACT",
    compute_create_address(address=root_deployer, nonce=current_root_nonce).hex(),
)
