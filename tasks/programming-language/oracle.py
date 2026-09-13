"""Host-only reference programs. Never installed in the agent image or given to a learner.

These helpers implement storage/printing/counted-loop idioms for a KNOWN language.
They prove solvability; they do not demonstrate that an agent learned the idioms.
"""

from contextlib import contextmanager

from language_game.engine import Language


class Builder:
    def __init__(self, language: Language):
        self.language = language
        self.pointer = 0
        self.code = ""

    def move(self, cell):
        if not 0 <= cell < self.language.tape_size:
            raise ValueError("reference program exceeds tape")
        delta = cell - self.pointer
        self.code += ">" * max(delta, 0) + "<" * max(-delta, 0)
        self.pointer = cell

    def add(self, cell, amount):
        self.move(cell)
        self.code += "+" * max(amount, 0) + "-" * max(-amount, 0)

    def set(self, cell, amount):
        self.move(cell)
        self.code += "[]" if self.language.loop_mode == "consume" else "[-]"
        self.add(cell, amount)

    def read(self, cell):
        if self.language.input_mode == "add":
            self.set(cell, 0)
        self.move(cell)
        self.code += ","

    def emit(self, cell, *, preserve=False):
        if preserve and self.language.output_mode == "clear":
            # Reserve cells 6 and 7 for printing without destroying a live value.
            self.copy(cell, 6, 7)
            cell = 6
        self.move(cell)
        self.code += "."

    @contextmanager
    def loop(self, cell):
        """Counted iteration: consume one unit before each body execution."""
        self.move(cell)
        self.code += "["
        if self.language.loop_mode == "manual":
            self.code += "-"
        yield
        self.move(cell)
        self.code += "]"

    def transfer(self, source, target):
        with self.loop(source):
            self.add(target, 1)

    def copy(self, source, target, scratch):
        if len({source, target, scratch}) != 3:
            raise ValueError("copy needs three distinct cells")
        self.set(target, 0)
        self.set(scratch, 0)
        with self.loop(source):
            self.add(target, 1)
            self.add(scratch, 1)
        self.transfer(scratch, source)


def reference_program(family: str, parameter: object, language: Language) -> str:
    b = Builder(language)
    if family == "constant":
        b.add(0, parameter)
        b.emit(0)
    elif family in ("echo", "successor", "duplicate", "overwrite"):
        b.read(0)
        if family == "overwrite":
            b.read(0)
        if family == "duplicate":
            b.emit(0, preserve=True)
        b.add(0, int(family == "successor"))
        b.emit(0)
    elif family == "add":
        b.read(0)
        b.read(1)
        b.transfer(1, 0)
        b.emit(0)
    elif family == "affine":
        b.read(0)
        b.set(1, parameter[1])
        with b.loop(0):
            b.add(1, parameter[0])
        b.emit(1)
    elif family == "equals":
        b.read(0)
        b.add(0, -parameter)
        b.set(1, 1)
        with b.loop(0):
            b.set(0, 0)
            b.set(1, 0)
        b.emit(1)
    elif family == "permute":
        for cell in range(3):
            b.read(cell)
        for cell in parameter:
            b.emit(cell - 1)
    elif family == "range":
        b.read(0)
        b.set(1, parameter)
        with b.loop(0):
            b.emit(1, preserve=True)
            b.add(1, 1)
    elif family == "repeat":
        b.read(0)
        b.read(1)
        b.add(1, parameter)
        with b.loop(0):
            b.emit(1, preserve=True)
    elif family in ("sum", "prefix", "count", "stream_echo", "totals"):
        b.read(0)
        b.set(1, parameter if family == "sum" else 0)
        with b.loop(0):
            b.read(2)
            if family == "count":
                with b.loop(2):
                    b.set(2, 0)
                    b.add(1, 1)
            elif family == "stream_echo":
                b.emit(2)
            else:
                if family == "totals":
                    b.emit(2, preserve=True)
                b.transfer(2, 1)
            if family == "prefix":
                b.emit(1, preserve=True)
        if family not in ("prefix", "stream_echo"):
            b.emit(1)
    elif family == "select":
        for cell in range(3):
            b.read(cell)
        b.set(3, 1)
        with b.loop(0):
            b.set(0, 0)
            b.set(3, 0)
            b.emit(2)
        with b.loop(3):
            b.set(3, 0)
            b.emit(1)
    elif family == "triangular":
        b.read(0)
        with b.loop(0):
            b.add(1, 1)
            b.copy(0, 2, 3)
            b.transfer(2, 1)
        b.emit(1)
    elif family == "pair_sums":
        b.read(0)
        with b.loop(0):
            b.read(1)
            b.read(2)
            b.transfer(2, 1)
            b.emit(1)
    elif family == "dot":
        b.read(0)
        with b.loop(0):
            b.read(1)
            b.read(2)
            with b.loop(1):
                b.copy(2, 3, 4)
                b.transfer(3, 5)
        b.emit(5)
    else:
        raise ValueError(f"unknown problem family: {family}")
    return b.code
