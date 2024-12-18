import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from PNGParser.PNG import PNGParser
from PNGParser.additionals import FilterType, ColorType, Parsing

image_name = "cubes.png"
image_path = Path(__file__).parent / image_name

class TestImageProcessing:
    @pytest.fixture
    def parser(self):
        return PNGParser(str(image_path))

    def test_decompress_image_data(self, parser):
        data = parser.read_file()
        parser.parse_chunks(data)
        parser.process_chunks()
        decompressed_data = parser.decompress_image_data()
        assert isinstance(decompressed_data, bytes), "Decompressed data should be bytes"
        assert len(decompressed_data) == 1920600, "Expected decompressed data length 1920600"

    def test_reconstruct_image(self, parser):
        data = parser.read_file()
        parser.parse_chunks(data)
        parser.process_chunks()
        decompressed_data = parser.decompress_image_data()
        image_data = parser.reconstruct_image(decompressed_data)
        assert isinstance(image_data, list), "Image data should be a list of rows"
        assert len(image_data) == 600, "Expected 600 rows for the height of 600 pixels"

    def test_apply_filter(self, parser):
        data = parser.read_file()
        parser.parse_chunks(data)
        parser.process_chunks()
        color_type = Parsing.parse_color_type(parser.IHDR_data.color_type)
        scanline = bytes([100, 100, 100, 255] * 5)
        result = parser.apply_filter(FilterType.NO_FILTER, color_type, scanline, None, 4)
        assert len(result) == 5, "Resulting row should contain 5 pixels"

    def test_paeth_predictor(self, parser):
        assert parser.paeth_predictor(133, 131, 129) == 133
        assert parser.paeth_predictor(10, 20, 30) == 10
        assert parser.paeth_predictor(20, 10, 15) == 15
        assert parser.paeth_predictor(0, 0, 0) == 0
