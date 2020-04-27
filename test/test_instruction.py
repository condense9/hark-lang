import json

import c9.machine.instructionset as instructionset
from c9.machine.instruction import Instruction
from c9.machine.instructionset import *
from c9.machine.types import *


def test_ser():
    instr = Jump(C9Int(5))
    ser = instr.serialise()
    deser = Instruction.deserialise(ser, instructionset)
    assert instr == deser


def test_jsonable():
    instr = Jump(C9Int(5))
    ser = instr.serialise()
    jser = json.dumps(ser)
    jdeser = json.loads(jser)
    deser = Instruction.deserialise(jdeser, instructionset)
    assert instr == deser
