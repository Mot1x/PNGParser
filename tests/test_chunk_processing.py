import pytest
import sys
from pathlib import Path
from PNGParser.PNG import PNGParser
from PNGParser.additionals import IHDRData, Parsing

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


class TestChunkProcessing:
    @pytest.fixture
    def parser(self, image_path):
        return PNGParser(image_path)

    def test_parse_chunks(self, parser):
        data = parser.read_file()
        parser.parse_chunks(data)
        assert len(parser.chunks) == 3, "Should contain IHDR, IDAT, and IEND chunks"
        assert any(chunk.type == "IHDR" for chunk in parser.chunks), "IHDR chunk should be present"
        assert sum(1 for chunk in parser.chunks if chunk.type == "IDAT") == 1, "Should contain 1 IDAT chunk"
        assert any(chunk.type == "IEND" for chunk in parser.chunks), "IEND chunk should be present"

    def test_process_chunks(self, parser):
        data = parser.read_file()
        parser.parse_chunks(data)
        parser.process_chunks()
        assert parser.IHDR_data is not None, "IHDR data should be parsed"
        assert isinstance(parser.IHDR_data, IHDRData), "IHDR data should be instance of IHDRData"
        assert parser.image_data != b"", "IDAT data should be collected"

    def test_parse_ihdr(self, parser):
        data = parser.read_file()
        parser.parse_chunks(data)
        ihdr_chunk = next(chunk for chunk in parser.chunks if chunk.type == "IHDR")
        ihdr_data = Parsing.bytes_to_IHDRData(ihdr_chunk.data)
        assert isinstance(ihdr_data, IHDRData), "IHDR data should be instance of IHDRData"
        assert ihdr_data.width == 800, "Expected width 800"
        assert ihdr_data.height == 600, "Expected height 600"
        assert ihdr_data.bit_depth == 8, "Expected bit depth 8"
        assert ihdr_data.color_type == 6, "Expected color type 6 (RGBA)"
