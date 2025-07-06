from ethereum_clis.types import TransitionToolInput
from ethereum_test_tools import Account, Alloc
from ethereum_test_tools.vm.opcode import Opcodes as Op
from ethereum_test_types.helpers import compute_create_address

BLOCK_GAS_LIMIT = 60_000_000
MIN_READ_COST = 2500
CODE_SIZE_MAX = 0x40000

accounts_necessary = BLOCK_GAS_LIMIT // MIN_READ_COST
alloc_dict = {}

for nonce in range(2):
    address = compute_create_address(
        address="0x36d466250593febc713b9208146a4331865eb00a", nonce=nonce
    )
    code_start = (Op.JUMP(Op.SUB(Op.CODESIZE, 1)) + Op.JUMP).__bytes__()
    code_addr = address.__bytes__()
    code = (code_start + code_addr).ljust(CODE_SIZE_MAX, Op.JUMPDEST.__bytes__())
    alloc_dict[address.hex()] = Account(code=code, nonce=1)


for i in range(1, 8):
    print(compute_create_address(address="0x735e9bB882B44771d03C9760Acc091dB55BFBf63", nonce=i))
