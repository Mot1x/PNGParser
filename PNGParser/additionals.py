import struct
from dataclasses import dataclass
from enum import Enum
from typing import List


class FilterType(Enum):
    NO_FILTER = 0
    SUB = 1
    UP = 2
    AVERAGE = 3
    PAETH = 4


@dataclass
class Pixel:
    R: int
    G: int
    B: int
    A: int = 0


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
    palette: List[Pixel]


class Parsing:
    @staticmethod
    def bytes_to_PLTEData(data: bytes) -> PLTEData:
        palette = []
        for i in range(0, len(data), 3):
            r, g, b = data[i:i + 3]
            palette.append(Pixel(R=r, G=g, B=b))
        return PLTEData(palette=palette)

    @staticmethod
    def bytes_to_IHDRData(data: bytes) -> IHDRData:
        width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack('>IIBBBBB', data)
        return IHDRData(
            width=width,
            height=height,
            bit_depth=bit_depth,
            color_type=color_type,
            compression=compression,
            filter_method=filter_method,
            interlace=interlace
        )

    @staticmethod
    def parse_color_type(color_type: int) -> ColorType:
        return ColorType(
            has_palette=bool(color_type & 1),
            has_color=bool(color_type & 2),
            has_alpha=bool(color_type & 4)
        )
