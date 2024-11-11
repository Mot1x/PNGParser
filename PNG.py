import struct
import zlib
from typing import List, Tuple
from dataclasses import dataclass
import tkinter as tk
from PIL import Image, ImageTk


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
    has_palette: bool
    has_color: bool
    has_alpha: bool


@dataclass
class PLTEData:
    palette: List[Tuple[int, int, int]]


class PNGParser:
    def __init__(self, file_path: str) -> None:
        self.plte_data = None
        self.file_path = file_path
        self.chunks: List[Chunk] = []
        self.IHDR_data: IHDRData | None = None
        self.image_data: bytes = b''

    def read_file(self) -> bytes:
        with open(self.file_path, 'rb') as f:
            data = f.read()
        return data

    def validate_signature(self, data: bytes) -> None:
        signature = data[:8]
        expected_signature = b'\x89PNG\r\n\x1a\n'
        if signature != expected_signature:
            raise ValueError("Invalid PNG signature.")

    def parse_chunks(self, data: bytes) -> None:
        offset = 8
        while offset < len(data):
            length, = struct.unpack('>I', data[offset:offset + 4])
            chunk_type = data[offset + 4:offset + 8].decode('ascii')
            chunk_data = data[offset + 8:offset + 8 + length]
            crc, = struct.unpack('>I', data[offset + 8 + length:offset + 12 + length])
            chunk = Chunk(length, chunk_type, chunk_data, crc)
            self.chunks.append(chunk)
            print(f"Found chunk: {chunk}")
            offset += length + 12

    def process_chunks(self) -> None:
        for chunk in self.chunks:
            if chunk.type == 'IHDR':
                self.IHDR_data = self.parse_ihdr(chunk.data)
                print(f"IHDR Data: {self.IHDR_data}")
            elif chunk.type == 'IDAT':
                self.image_data += chunk.data
            elif chunk.type == 'PLTE':
                self.plte_data = self.parse_plte(chunk.data)
            elif chunk.type == 'IEND':
                print("Reached IEND chunk.")
                break

    def parse_ihdr(self, data: bytes) -> IHDRData:
        fields = struct.unpack('>IIBBBBB', data)
        ihdr = IHDRData(*fields)
        return ihdr

    def parse_plte(self, data: bytes) -> PLTEData:
        palette = []
        for i in range(0, len(data), 3):
            r, g, b = struct.unpack('BBB', data[i:i + 3])
            palette.append((r, g, b))
        return PLTEData(palette)

    def decompress_image_data(self) -> bytes:
        decompressed_data = zlib.decompress(self.image_data)
        print(f"Decompressed image data length: {len(decompressed_data)}")
        return decompressed_data

    def parse_color_type(self) -> ColorType:
        color_type = self.IHDR_data.color_type
        has_palette = False
        has_color = False
        has_alpha = False

        if color_type >= 4:
            has_alpha = True
            color_type -= 4
        if color_type >= 2:
            has_color = True
            color_type -= 2
        if color_type == 1:
            has_palette = True
            color_type -= 1
        if color_type != 0:
            raise Exception("Invalid color type")
        return ColorType(has_palette, has_color, has_alpha)

    def reconstruct_image(self, decompressed_data: bytes) -> List[List[Tuple[int, int, int, int]]]:
        width = self.IHDR_data.width
        height = self.IHDR_data.height
        color_type = self.parse_color_type()

        bytes_per_pixel = 3
        if color_type.has_palette:
            bytes_per_pixel = 1
        elif color_type.has_alpha:
            bytes_per_pixel = 4

        stride = width * bytes_per_pixel
        image = []
        offset = 0
        for y in range(height):
            filter_type = decompressed_data[offset]
            offset += 1
            scanline = decompressed_data[offset:offset + stride]
            offset += stride
            if filter_type == 0:
                if color_type.has_palette:
                    row = [self.plte_data.palette[scanline[i]] for i in range(len(scanline))]
                elif color_type.has_alpha:
                    row = [(scanline[i], scanline[i + 1], scanline[i + 2], scanline[i + 3]) for i in
                           range(0, len(scanline), bytes_per_pixel)]
                else:
                    row = [(scanline[i], scanline[i + 1], scanline[i + 2]) for i in
                           range(0, len(scanline), bytes_per_pixel)]
            else:
                row = self.apply_filter(filter_type, color_type, scanline, image[y - 1] if y > 0 else None,
                                        bytes_per_pixel)
            image.append(row)
        print(f"Reconstructed image with {len(image)} rows.")
        return image

    def apply_filter(self, filter_type: int, color_type: ColorType, scanline: bytes,
                     prev_row: List[Tuple[int, int, int, int]] | None,
                     bpp: int) -> List[Tuple[int, int, int, int]]:
        filtered_row = []
        for i in range(0, len(scanline), bpp):
            pixel = scanline[i:i + bpp]
            if filter_type == 1:
                if color_type.has_palette:
                    left_index = filtered_row[i - 1] if i > 0 else 0
                    filtered_pixel = self.plte_data.palette[(pixel[0] + left_index) % 256]
                else:
                    filtered_pixel = tuple(
                        (pixel[j] + (filtered_row[-1][j] if len(filtered_row) > 0 else 0)) % 256 for j in range(bpp))

            elif filter_type == 2:
                if color_type.has_palette:
                    up_index = prev_row[i] if prev_row else 0
                    filtered_pixel = self.plte_data.palette[(pixel[0] + up_index) % 256]
                else:
                    filtered_pixel = tuple(
                        (pixel[j] + (prev_row[i // bpp][j] if prev_row else 0)) % 256 for j in range(bpp))

            elif filter_type == 3:
                left = filtered_row[-1] if len(filtered_row) > 0 else (0, 0, 0, 0)
                up = prev_row[i // bpp] if prev_row else (0, 0, 0, 0)
                filtered_pixel = tuple((pixel[j] + ((left[j] + up[j]) // 2)) % 256 for j in range(bpp))
                if color_type.has_palette:
                    filtered_pixel = self.plte_data(filtered_pixel[0])

            elif filter_type == 4:
                left = filtered_row[-1] if len(filtered_row) > 0 else (0, 0, 0, 0)
                up = prev_row[i // bpp] if prev_row else (0, 0, 0, 0)
                upleft = prev_row[i // bpp - 1] if (prev_row and i >= bpp) else (0, 0, 0, 0)
                filtered_pixel = tuple(
                    (pixel[j] + self.paeth_predictor(left[j], up[j], upleft[j])) % 256 for j in range(bpp))
                if color_type.has_palette:
                    filtered_pixel = self.plte_data(filtered_pixel[0])

            else:
                filtered_pixel = tuple(pixel)
            filtered_row.append(filtered_pixel)
        return filtered_row

    def paeth_predictor(self, a: int, b: int, c: int) -> int:
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        elif pb <= pc:
            return b
        return c

    def display_image(self, image_data: List[List[Tuple[int, int, int, int]]]) -> None:
        width = self.IHDR_data.width
        height = self.IHDR_data.height
        image = Image.new('RGBA', (width, height))
        pixels = []
        for row in image_data:
            for pixel in row:
                pixels.append(pixel)
        image.putdata(pixels)
        root = tk.Tk()
        tk_image = ImageTk.PhotoImage(image)
        label = tk.Label(root, image=tk_image)
        label.pack()
        root.mainloop()

    def parse(self) -> None:
        data = self.read_file()
        self.validate_signature(data)
        self.parse_chunks(data)
        self.process_chunks()
        decompressed_data = self.decompress_image_data()
        image_data = self.reconstruct_image(decompressed_data)
        self.print_chunk_info()
        self.display_image(image_data)

    def print_chunk_info(self) -> None:
        print(f"File size: {len(self.read_file())} bytes")
        for chunk in self.chunks:
            print(f"Chunk Type: {chunk.type}, Length: {chunk.length}")


if __name__ == '__main__':
    parser = PNGParser('cat5 (2).png')
    parser.parse()
