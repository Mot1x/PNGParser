import pytest
import os
import sys

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)
from PNGParser.PNG import PNGParser, ColorType
from PNGParser.additionals import FilterType, IHDRData, Parsing

image_name = "cubes.png"
image_path = os.path.abspath(os.path.join(os.path.dirname(__file__), image_name))


@pytest.fixture
def parser():
    return PNGParser(image_path)


def test_read_file(parser):
    data = parser.read_file()
    assert isinstance(data, bytes), "Data should has bytes type"
    assert len(data) > 0, "File should not be empty"


def test_validate_signature(parser):
    data = parser.read_file()
    try:
        parser.validate_signature(data)
    except ValueError:
        pytest.fail("Validation failed with correct signature")

    with pytest.raises(ValueError):
        parser.validate_signature(b"incorrect_signature")


def test_parse_chunks(parser):
    data = parser.read_file()
    parser.parse_chunks(data)
    assert len(parser.chunks) == 3, "Should contain IHDR, IDAT, and IEND chunks"
    assert any(chunk.type == "IHDR" for chunk in parser.chunks), "IHDR chunk should be present"
    assert sum(1 for chunk in parser.chunks if chunk.type == "IDAT") == 1, "Should contain 1 IDAT chunk"
    assert any(chunk.type == "IEND" for chunk in parser.chunks), "IEND chunk should be present"


def test_process_chunks(parser):
    data = parser.read_file()
    parser.parse_chunks(data)
    parser.process_chunks()
    assert parser.IHDR_data is not None, "IHDR data should be parsed"
    assert isinstance(parser.IHDR_data, IHDRData), "IHDR data should be instance of IHDRData"
    assert parser.image_data != b"", "IDAT data should be collected"


def test_parse_ihdr(parser):
    data = parser.read_file()
    parser.parse_chunks(data)
    ihdr_chunk = next(chunk for chunk in parser.chunks if chunk.type == "IHDR")
    ihdr_data = Parsing.bytes_to_IHDRData(ihdr_chunk.data)
    assert isinstance(ihdr_data, IHDRData), "IHDR data should be instance of IHDRData"
    assert ihdr_data.width == 800, "Expected width 800"
    assert ihdr_data.height == 600, "Expected height 600"
    assert ihdr_data.bit_depth == 8, "Expected bit depth 8"
    assert ihdr_data.color_type == 6, "Expected color type 6 (RGBA)"


def test_decompress_image_data(parser):
    data = parser.read_file()
    parser.parse_chunks(data)
    parser.process_chunks()
    decompressed_data = parser.decompress_image_data()
    assert isinstance(decompressed_data, bytes), "Decompressed data should be bytes"
    assert len(decompressed_data) == 1920600, "Expected decompressed data length 1920600"


def test_parse_color_type(parser):
    data = parser.read_file()
    parser.parse_chunks(data)
    parser.process_chunks()
    color_type = Parsing.parse_color_type(parser.IHDR_data.color_type)
    assert isinstance(color_type, ColorType), "Color type should be instance of ColorType"
    assert color_type.has_color is True, "Expected color to be present"
    assert color_type.has_alpha is True, "Expected alpha channel to be present"
    assert color_type.has_palette is False, "Expected no palette"


def test_reconstruct_image(parser):
    data = parser.read_file()
    parser.parse_chunks(data)
    parser.process_chunks()
    decompressed_data = parser.decompress_image_data()
    image_data = parser.reconstruct_image(decompressed_data)
    assert isinstance(image_data, list), "Image data should be a list of rows"
    assert len(image_data) == 600, "Expected 600 rows for the height of 600 pixels"


def test_apply_filter(parser):
    data = parser.read_file()
    parser.parse_chunks(data)
    parser.process_chunks()
    color_type = Parsing.parse_color_type(parser.IHDR_data.color_type)
    scanline = bytes([100, 100, 100, 255] * 5)
    result = parser.apply_filter(FilterType.NO_FILTER, color_type, scanline, None, 4)
    assert len(result) == 5, "Resulting row should contain 5 pixels"


def test_paeth_predictor(parser):
    assert parser.paeth_predictor(133, 131, 129) == 133
    assert parser.paeth_predictor(10, 20, 30) == 10
    assert parser.paeth_predictor(20, 10, 15) == 15
    assert parser.paeth_predictor(0, 0, 0) == 0


def test_print_chunk_info(parser, capsys):
    data = parser.read_file()
    parser.parse_chunks(data)
    parser.print_chunk_info()
    captured = capsys.readouterr()
    assert "Chunk Type: IHDR" in captured.out
    assert "Chunk Type: IDAT" in captured.out
    assert "Chunk Type: IEND" in captured.out
    assert "File size: 224566 bytes" in captured.out


def test_all_functions(parser):
    parser.parse()