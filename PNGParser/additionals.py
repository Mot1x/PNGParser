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


@dataclass
class ColorType:
    has_palette: bool = False
    has_color: bool = False
    has_alpha: bool = False


@dataclass
class PLTEData:
    palette: List[Tuple[int, int, int]]


@dataclass
class Pixel:
    R: int
    G: int
    B: int
    A: int = 0


class Parsing:
    @staticmethod
    def bytes_to_PLTEData(data: bytes) -> PLTEData:
        palette = []
        for i in range(0, len(data), 3):
            r, g, b = struct.unpack('BBB', data[i:i + 3])
            palette.append((r, g, b))
        return PLTEData(palette)

    @staticmethod
    def bytes_to_IHDRData(data: bytes) -> IHDRData:
        fields = struct.unpack('>IIBBBBB', data)
        return IHDRData(*fields)

    @staticmethod
    def parse_color_type(color_type: int) -> ColorType:
        color = ColorType()
        if color_type >= 4:
            color.has_alpha = True
            color_type -= 4
        if color_type >= 2:
            color.has_color = True
            color_type -= 2
        if color_type == 1:
            color.has_palette = True
            color_type -= 1
        if color_type != 0:
            raise Exception("Invalid color type")
        return color
