import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from PNGParser.PNG import PNGParser, ColorType
from PNGParser.additionals import Parsing

image_name = "cubes.png"
image_path = Path(__file__).parent / image_name

class TestDataStructures:
    @pytest.fixture
    def parser(self):
        return PNGParser(str(image_path))

    def test_parse_color_type(self, parser):
        data = parser.read_file()
        parser.parse_chunks(data)
        parser.process_chunks()
        color_type = Parsing.parse_color_type(parser.IHDR_data.color_type)
        assert isinstance(color_type, ColorType), "Color type should be instance of ColorType"
        assert color_type.has_color is True, "Expected color to be present"
        assert color_type.has_alpha is True, "Expected alpha channel to be present"
        assert color_type.has_palette is False, "Expected no palette"

    def test_integration(self, parser):
        """Integration test to ensure all components work together"""
        parser.parse()
        assert parser.IHDR_data is not None
        assert parser.image_data is not None
        assert len(parser.chunks) > 0
