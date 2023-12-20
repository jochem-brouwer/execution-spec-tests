"""
abstract: Test MODEXP (0x0000..0005)

    Tests the MODEXP precompile, located at address 0x0000..0005

"""
import pytest

from ethereum_test_forks import Frontier
from ethereum_test_tools import (
    Account,
    Environment,
    StateTestFiller,
    Storage,
    Transaction,
    to_address,
)

def input(b: str, e: str, m: str, extra: str):
    return '0x' + f'{int(len(b)/2):x}'.zfill(64) + f'{int(len(e)/2):x}'.zfill(64) + f'{int(len(m)/2):x}'.zfill(64) + b + e + m + extra
    
    
# ModExp is available since Byzantium
@pytest.mark.valid_from("Byzantium")
def test_modexp(state_test: StateTestFiller):
    """
        Test the MODEXP precompile
    """
    env = Environment()
    pre = {"0xa94f5374fce5edbc8e2a8697c15331677e6ebf0b": Account(balance=1000000000000000000000)}
    post = {}

    account = to_address(0x100)

    # format: [b, e, m, output, extraData?]
    # Here, `b`, `e` and `m` are the inputs to the ModExp precompile
    # The output is the expected output of the call
    # The optional extraData is extra padded data at the end of the calldata to the precompile
    data = [
        ['', '', '02', '0x01'],
        ['', '', '0002', '0x0001'],
        ['00', '00', '02', '0x01'],
        ['', '01', '02', '0x00'],
        ['01', '01', '02', '0x01'],
        ['02', '01', '03', '0x02'],
        ['02', '02', '05', '0x04'],
        ['', '', '', '0x'],
        ['', '', '00', '0x00'],
        ['', '', '01', '0x00'],
        ['', '', '0001', '0x0000'],
        # Test cases from EIP 198 (Note: the cases where the call goes OOG and the final test case are not yet tested)
        ['03', 
         'fffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2e', 
         'fffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f', 
         '0000000000000000000000000000000000000000000000000000000000000001'],
         ['',
          'fffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2e',
          'fffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f',
          '0000000000000000000000000000000000000000000000000000000000000000'],
         ['03', 
          'ffff', 
          '8000000000000000000000000000000000000000000000000000000000000000', 
          '0x3b01b01ac41f2d6e917c6d6a221ce793802469026d9ab7578fa2e79e4da6aaab', 
          '07'],

    ]

    for entry in data:
        pre[account] = Account(
            code=(
                # Store all CALLDATA into memory (offset 0)
                """0x366000600037"""
                +
                # Setup stack to CALL into ModExp with the CALLDATA and CALL into it (+ pop value)
                """60006000366000600060055AF150"""
                +
                # Store contract deployment code to deploy the returned data from ModExp as contract code (16 bytes)
                """7F601038036010600039601038036000F300000000000000000000000000000000600052""" 
                +
                # RETURNDATACOPY the returned data from ModExp into memory (offset 16 bytes)
                """3D600060103E"""
                + 
                # CREATE contract with the deployment code + the returned data from ModExp
                """3D60100160006000F0"""
                + 
                # STOP (handy for tracing)
                "00"
            )
        )

        extra = ""
        if (len(entry) == 5):
            extra = entry[4]

        tx = Transaction(
            ty=0x0,
            nonce=0,
            to=account,
            data=input(entry[0], entry[1], entry[2], extra),
            gas_limit=500000,
            gas_price=10,
            protected=True,
        )
        # This is the address of the contract which gets generated once the contract at 0x100 is invoked
        post["0xa7f2bd73a7138a2dec709484ad9c3542d7bc7534"] = Account(code=entry[3])

        state_test(env=env, pre=pre, post=post, txs=[tx])