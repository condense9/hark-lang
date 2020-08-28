import json

import hark_lang.machine.instructionset as instructionset
from hark_lang.machine.instruction import Instruction
from hark_lang.machine.instructionset import *
from hark_lang.machine.types import *


def test_ser():
    instr = Jump(TlInt(5))
    ser = instr.serialise()
    deser = Instruction.deserialise(ser, instructionset)
    assert instr == deser


def test_jsonable():
    instr = Jump(TlInt(5))
    ser = instr.serialise()
    jser = json.dumps(ser)
    jdeser = json.loads(jser)
    deser = Instruction.deserialise(jdeser, instructionset)
    assert instr == deser
