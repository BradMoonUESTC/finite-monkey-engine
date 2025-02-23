from typing import Any
from antlr4 import CommonTokenStream
from src.library.parsing.SolidityParser import getSubcontract, parseToken

SUBCONTRACT_ID = "subcontract"

class SolidityParser:
    def __init__(self):
        pass

    def parse_stream(self, stream: CommonTokenStream) -> list:
        result = []
        max_length = len(stream.tokens)
        i = 0

        while i < max_length:
            id, content, loc = parseToken(str(stream.tokens[i]))
            if id is not None:
                if id == SUBCONTRACT_ID:
                    i, subcontract, subcontract_entry = getSubcontract(i+1, stream.tokens, max_length, id, loc)
                    result.append(subcontract_entry)

        return result