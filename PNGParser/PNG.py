import dataclasses
import struct
import zlib
import tkinter as tk
import matplotlib
from PIL import Image, ImageTk
from pathlib import Path
from PNGParser.additionals import Chunk, IHDRData, PLTEData, ColorType, FilterType, Parsing, Pixel
import matplotlib.pyplot as plt

matplotlib.use('TkAgg')


class PNGParser:
    def __init__(self, file_path: Path) -> None:
        self._PLTE_data: PLTEData | None = None
        self._file_path: Path = Path(file_path)
        self.chunks: list[Chunk] = []
        self.IHDR_data: IHDRData | None = None
        self.image_data: bytes = b''
        self.image: list[list[Pixel]] = []
        self.scaling_factor: float = 1.0

    def read_file(self) -> bytes:
        try:
            with self._file_path.open('rb') as png_file:
                return png_file.read()
        except FileNotFoundError:
            raise ValueError(f"File not found: {self._file_path}")
        except IOError as e:
            raise ValueError(f"Error reading the file {self._file_path}: {e}")

    def validate_signature(self, png_data: bytes) -> None:
        header_length: int = 8
        file_signature: bytes = png_data[:header_length]
        expected_signature: bytes = b'\x89PNG\r\n\x1a\n'
        if file_signature != expected_signature:
            raise ValueError(f"Invalid PNG signature. Expected {expected_signature}, but got {file_signature}.")

    def parse_chunks(self, png_data: bytes) -> None:
        current_offset: int = 8
        while current_offset < len(png_data):
            try:
                chunk_length: int = struct.unpack('>I', png_data[current_offset:current_offset + 4])[0]
                chunk_type: str = png_data[current_offset + 4:current_offset + 8].decode('ascii')
                chunk_data: bytes = png_data[current_offset + 8:current_offset + 8 + chunk_length]
                chunk_crc: int = \
                    struct.unpack('>I', png_data[current_offset + 8 + chunk_length:current_offset + 12 + chunk_length])[
                        0]
                current_chunk = Chunk(chunk_length, chunk_type, chunk_data, chunk_crc)
                self.chunks.append(current_chunk)
                current_offset += chunk_length + 12
            except struct.error:
                raise ValueError(f"Error parsing chunk at offset {current_offset}. Invalid chunk structure.")
            except Exception as e:
                raise ValueError(f"Error parsing chunk at offset {current_offset}: {e}")

    def process_chunks(self) -> None:
        for chunk in self.chunks:
            try:
                if chunk.type == 'IHDR':
                    self.IHDR_data = Parsing.bytes_to_IHDRData(chunk.data)
                elif chunk.type == 'IDAT':
                    self.image_data += chunk.data
                elif chunk.type == 'PLTE':
                    self._PLTE_data = Parsing.bytes_to_PLTEData(chunk.data)
                elif chunk.type == 'IEND':
                    break
            except Exception as e:
                raise ValueError(f"Error processing chunk {chunk.type}: {e}")

    def decompress_image_data(self) -> bytes:
        try:
            decompressed_data: bytes = zlib.decompress(self.image_data)
            return decompressed_data
        except zlib.error as e:
            raise ValueError(f"Error decompressing image data: {e}")

    def reconstruct_image(self, decompressed_data: bytes) -> list[list[Pixel]]:
        try:
            image_width: int = self.IHDR_data.width
            image_height: int = self.IHDR_data.height
            color_type: ColorType = Parsing.parse_color_type(self.IHDR_data.color_type)
            bytes_per_pixel: int = self._calculate_bytes_per_pixel(color_type)

            stride = image_width * bytes_per_pixel
            image = []
            offset = 0
            for y in range(image_height):
                filter_type = FilterType(decompressed_data[offset])
                offset += 1
                scanline = decompressed_data[offset:offset + stride]
                offset += stride
                row = self.apply_filter(filter_type, color_type, scanline, image[y - 1] if y > 0 else None,
                                        bytes_per_pixel)
                image.append(row)
            return image
        except AttributeError:
            raise ValueError("IHDR data is missing or corrupted.")
        except Exception as e:
            raise ValueError(f"Error reconstructing image: {e}")

    def _calculate_bytes_per_pixel(self, color_type: ColorType) -> int:
        if color_type.has_palette:
            return 1
        if color_type.has_alpha:
            return 4
        return 3

    def apply_filter(self, filter_type: FilterType, color_type: ColorType, scanline: bytes,
                     prev_row: list[Pixel] | None,
                     bytes_per_pixel: int) -> list[Pixel]:
        try:
            filtered_row = []

            if filter_type == FilterType.NO_FILTER:
                return self._apply_no_filter(bytes_per_pixel, color_type, scanline)

            for pixel_index in range(0, len(scanline), bytes_per_pixel):
                current_pixel: bytes = scanline[pixel_index:pixel_index + bytes_per_pixel]

                if filter_type == FilterType.SUB:
                    filtered_pixel = self._apply_sub_filter(bytes_per_pixel, color_type, filtered_row, pixel_index,
                                                            current_pixel)
                elif filter_type == FilterType.UP:
                    filtered_pixel = self._apply_up_filter(bytes_per_pixel, color_type, pixel_index, current_pixel,
                                                           prev_row)
                elif filter_type == FilterType.AVERAGE:
                    filtered_pixel = self._apply_average_filter(bytes_per_pixel, color_type, filtered_row, pixel_index,
                                                                current_pixel, prev_row)
                elif filter_type == FilterType.PAETH:
                    filtered_pixel = self._apply_paeth_filter(bytes_per_pixel, color_type, filtered_row, pixel_index,
                                                              current_pixel, prev_row)
                else:
                    filtered_pixel = self._bytes_to_pixel(current_pixel, bytes_per_pixel)
                filtered_row.append(filtered_pixel)
            return filtered_row
        except Exception as e:
            raise ValueError(f"Error applying filter {filter_type}: {e}")

    def _bytes_to_pixel(self, pixel_bytes: bytes, bytes_per_pixel: int) -> Pixel:
        try:
            if bytes_per_pixel == 4:
                return Pixel(R=pixel_bytes[0], G=pixel_bytes[1], B=pixel_bytes[2], A=pixel_bytes[3])
            if bytes_per_pixel == 3:
                return Pixel(R=pixel_bytes[0], G=pixel_bytes[1], B=pixel_bytes[2])
            return Pixel(R=0, G=0, B=0)
        except IndexError:
            raise ValueError("Invalid pixel data: unable to map bytes to pixel.")

    def _apply_no_filter(self, bytes_per_pixel: int, color_type: ColorType,
                         scanline: bytes) -> list[Pixel]:
        try:
            if color_type.has_palette:
                return [self._PLTE_data.palette[scanline[i]] for i in range(len(scanline))]

            pixels = []
            for i in range(0, len(scanline), bytes_per_pixel):
                pixel_bytes = scanline[i:i + bytes_per_pixel]
                pixels.append(self._bytes_to_pixel(pixel_bytes, bytes_per_pixel))
            return pixels
        except Exception as e:
            raise ValueError(f"Error applying no filter: {e}")

    def _apply_sub_filter(self, bytes_per_pixel: int, color_type: ColorType, filtered_row: list[Pixel],
                          pixel_index: int,
                          pixel: bytes) -> Pixel:
        if color_type.has_palette:
            left_value: int = filtered_row[pixel_index - 1].R if pixel_index > 0 else 0
            return self._PLTE_data.palette[(pixel[0] + left_value) % 256]

        left_pixel = filtered_row[-1] if filtered_row else Pixel(0, 0, 0, 0)
        if bytes_per_pixel == 4:
            return Pixel(
                R=(pixel[0] + left_pixel.R) % 256,
                G=(pixel[1] + left_pixel.G) % 256,
                B=(pixel[2] + left_pixel.B) % 256,
                A=(pixel[3] + left_pixel.A) % 256
            )
        return Pixel(
            R=(pixel[0] + left_pixel.R) % 256,
            G=(pixel[1] + left_pixel.G) % 256,
            B=(pixel[2] + left_pixel.B) % 256
        )

    def _apply_up_filter(self, bytes_per_pixel: int, color_type: ColorType,
                         pixel_index: int, pixel: bytes,
                         prev_row: list[Pixel]) -> Pixel:
        if color_type.has_palette:
            up_value: int = prev_row[pixel_index].R if prev_row else 0
            return self._PLTE_data.palette[(pixel[0] + up_value) % 256]

        up_pixel = prev_row[pixel_index // bytes_per_pixel] if prev_row else Pixel(0, 0, 0, 0)
        if bytes_per_pixel == 4:
            return Pixel(
                R=(pixel[0] + up_pixel.R) % 256,
                G=(pixel[1] + up_pixel.G) % 256,
                B=(pixel[2] + up_pixel.B) % 256,
                A=(pixel[3] + up_pixel.A) % 256
            )
        return Pixel(
            R=(pixel[0] + up_pixel.R) % 256,
            G=(pixel[1] + up_pixel.G) % 256,
            B=(pixel[2] + up_pixel.B) % 256
        )

    def _apply_average_filter(self, bytes_per_pixel: int, color_type: ColorType,
                              filtered_row: list[Pixel], pixel_index: int,
                              pixel: bytes, prev_row: list[Pixel]) -> Pixel:
        left_pixel = filtered_row[-1] if filtered_row else Pixel(0, 0, 0, 0)
        up_pixel = prev_row[pixel_index // bytes_per_pixel] if prev_row else Pixel(0, 0, 0, 0)

        if color_type.has_palette:
            avg = ((left_pixel.R + up_pixel.R) // 2)
            return self._PLTE_data.palette[(pixel[0] + avg) % 256]

        if bytes_per_pixel == 4:
            return Pixel(
                R=(pixel[0] + ((left_pixel.R + up_pixel.R) // 2)) % 256,
                G=(pixel[1] + ((left_pixel.G + up_pixel.G) // 2)) % 256,
                B=(pixel[2] + ((left_pixel.B + up_pixel.B) // 2)) % 256,
                A=(pixel[3] + ((left_pixel.A + up_pixel.A) // 2)) % 256
            )
        return Pixel(
            R=(pixel[0] + ((left_pixel.R + up_pixel.R) // 2)) % 256,
            G=(pixel[1] + ((left_pixel.G + up_pixel.G) // 2)) % 256,
            B=(pixel[2] + ((left_pixel.B + up_pixel.B) // 2)) % 256
        )

    def _apply_paeth_filter(self, bytes_per_pixel: int, color_type: ColorType,
                            filtered_row: list[Pixel], pixel_index: int,
                            pixel: bytes, prev_row: list[Pixel]) -> Pixel:
        left_pixel = filtered_row[-1] if filtered_row else Pixel(0, 0, 0, 0)
        up_pixel = prev_row[pixel_index // bytes_per_pixel] if prev_row else Pixel(0, 0, 0, 0)
        upleft_pixel = (prev_row[pixel_index // bytes_per_pixel - 1]
                        if (prev_row and pixel_index >= bytes_per_pixel) else Pixel(0, 0, 0, 0))

        if color_type.has_palette:
            paeth = self.paeth_predictor(left_pixel.R, up_pixel.R, upleft_pixel.R)
            return self._PLTE_data.palette[(pixel[0] + paeth) % 256]

        if bytes_per_pixel == 4:
            return Pixel(
                R=(pixel[0] + self.paeth_predictor(left_pixel.R, up_pixel.R, upleft_pixel.R)) % 256,
                G=(pixel[1] + self.paeth_predictor(left_pixel.G, up_pixel.G, upleft_pixel.G)) % 256,
                B=(pixel[2] + self.paeth_predictor(left_pixel.B, up_pixel.B, upleft_pixel.B)) % 256,
                A=(pixel[3] + self.paeth_predictor(left_pixel.A, up_pixel.A, upleft_pixel.A)) % 256
            )
        return Pixel(
            R=(pixel[0] + self.paeth_predictor(left_pixel.R, up_pixel.R, upleft_pixel.R)) % 256,
            G=(pixel[1] + self.paeth_predictor(left_pixel.G, up_pixel.G, upleft_pixel.G)) % 256,
            B=(pixel[2] + self.paeth_predictor(left_pixel.B, up_pixel.B, upleft_pixel.B)) % 256
        )

    def paeth_predictor(self, a: int, b: int, c: int) -> int:
        p: int = a + b - c
        pa: int = abs(p - a)
        pb: int = abs(p - b)
        pc: int = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        if pb <= pc:
            return b
        return c

    def build_histogram(self) -> None:
        try:
            pixel_values = [pixel for row in self.image for pixel in row]
            r_values = [pixel.R for pixel in pixel_values]
            g_values = [pixel.G for pixel in pixel_values]
            b_values = [pixel.B for pixel in pixel_values]
            a_values = [pixel.A for pixel in pixel_values]

            fig = plt.figure(figsize=(8, 12))

            gs = fig.add_gridspec(3, 2)

            ax1 = fig.add_subplot(gs[0, 0])
            ax1.hist(r_values, bins=256, color='red', alpha=0.7, rwidth=0.85, log=True)
            ax1.set_title('Red')
            ax1.set_xlim(0, 255)

            ax2 = fig.add_subplot(gs[0, 1])
            ax2.hist(g_values, bins=256, color='green', alpha=0.7, rwidth=0.85, log=True)
            ax2.set_title('Green')
            ax2.set_xlim(0, 255)

            ax3 = fig.add_subplot(gs[1, 0])
            ax3.hist(b_values, bins=256, color='blue', alpha=0.7, rwidth=0.85, log=True)
            ax3.set_title('Blue')
            ax3.set_xlim(0, 255)

            ax4 = fig.add_subplot(gs[1, 1])
            ax4.hist(a_values, bins=256, color='gray', alpha=0.7, rwidth=0.85, log=True)
            ax4.set_title('Alpha')
            ax4.set_xlim(0, 255)

            ax5 = fig.add_subplot(gs[2, 0:])
            ax5.hist(r_values, bins=256, color='red', alpha=0.3, rwidth=0.85, log=True)
            ax5.hist(g_values, bins=256, color='green', alpha=0.3, rwidth=0.85, log=True)
            ax5.hist(b_values, bins=256, color='blue', alpha=0.3, rwidth=0.85, log=True)
            ax5.hist(a_values, bins=256, color='gray', alpha=0.3, rwidth=0.85, log=True)
            ax5.set_title('General')
            ax5.set_xlim(0, 255)

            plt.tight_layout()
            plt.show()
        except Exception as e:
            raise ValueError(f"Error building histogram: {e}")

    def scale_image(self) -> None:
        if self.scaling_factor != 1.0:
            image_width = int(self.IHDR_data.width * self.scaling_factor)
            image_height = int(self.IHDR_data.height * self.scaling_factor)

            image = Image.new('RGBA', (self.IHDR_data.width, self.IHDR_data.height))
            pixels = [dataclasses.astuple(pixel) for row in self.image for pixel in row]
            image.putdata(pixels)

            scaled_image = image.resize((image_width, image_height), Image.Resampling.LANCZOS)
            scaled_pixels = scaled_image.load()

            self.image = [
                [Pixel(*scaled_pixels[x, y]) for x in range(image_width)]
                for y in range(image_height)
            ]
            self.IHDR_data.width, self.IHDR_data.height = image_width, image_height

    def _display_image(self) -> None:
        image_width: int = self.IHDR_data.width
        image_height: int = self.IHDR_data.height
        image = Image.new('RGBA', (image_width, image_height))
        pixels = [dataclasses.astuple(pixel) for row in self.image for pixel in row]
        image.putdata(pixels)
        root = tk.Tk()
        tk_image = ImageTk.PhotoImage(image)
        label = tk.Label(root, image=tk_image)
        label.pack()
        root.mainloop()

    def parse(self, scale_percentage: float = 100.0) -> None:
        self.scaling_factor = scale_percentage / 100.0
        png_data = self.read_file()
        self.validate_signature(png_data)
        self.parse_chunks(png_data)
        self.process_chunks()
        decompressed_data = self.decompress_image_data()
        self.image = self.reconstruct_image(decompressed_data)
        self.scale_image()
        self.build_histogram()
        self._display_image()

    def print_chunk_info(self) -> None:
        print(f"File size: {len(self.read_file())} bytes")
        for chunk in self.chunks:
            print(f"Chunk Type: {chunk.type}, Length: {chunk.length}")


if __name__ == '__main__':
    image_path = Path(__file__).parent.parent / "tests" / "cubes.png"
    parser = PNGParser(image_path)
    parser.parse(50)
