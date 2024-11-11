import struct
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple


class FilterType(Enum):
    NO_FILTER = 0
    SUB = 1
    UP = 2
    AVERAGE = 3
    PAETH = 4


@dataclass
class Chunk:
    length: int
    type: str
    data: bytes
    crc: int

    def __repr__(self) -> str:
        return f"Chunk(type={self.type}, length={self.length})"


@dataclass
class IHDRData:
    width: int
    height: int
    bit_depth: int
    color_type: int
    compression: int
    filter_method: int
    interlace: int

    def __init__(self, data: bytes):
        fields = struct.unpack('>IIBBBBB', data)
        (self.width, self.height, self.bit_depth,
         self.color_type, self.compression, self.filter_method, self.interlace) = fields


@dataclass
class ColorType:
    has_palette: bool = False
    has_color: bool = False
    has_alpha: bool = False

    def __init__(self, color_type: int):
        if color_type >= 4:
            self.has_alpha = True
            color_type -= 4
        if color_type >= 2:
            self.has_color = True
            color_type -= 2
        if color_type == 1:
            self.has_palette = True
            color_type -= 1
        if color_type != 0:
            raise Exception("Invalid color type")


@dataclass
class PLTEData:
    palette: List[Tuple[int, int, int]]

    def __init__(self, data: bytes):
        palette = []
        for i in range(0, len(data), 3):
            r, g, b = struct.unpack('BBB', data[i:i + 3])
            palette.append((r, g, b))
        self.palette = palette
