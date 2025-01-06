import pytest
import sys
from pathlib import Path
from PNGParser.PNG import PNGParser

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


class TestFileOperations:
    @pytest.fixture
    def parser(self, image_path):
        return PNGParser(image_path)

    def test_read_file(self, parser):
        data = parser.read_file()
        assert isinstance(data, bytes), "Data should has bytes type"
        assert len(data) > 0, "File should not be empty"

    def test_validate_signature(self, parser):
        data = parser.read_file()
        try:
            parser.validate_signature(data)
        except ValueError:
            pytest.fail("Validation failed with correct signature")

        with pytest.raises(ValueError):
            parser.validate_signature(b"incorrect_signature")

    def test_print_chunk_info(self, parser, capsys):
        data = parser.read_file()
        parser.parse_chunks(data)
        parser.print_chunk_info()
        captured = capsys.readouterr()
        assert "Chunk Type: IHDR" in captured.out
        assert "Chunk Type: IDAT" in captured.out
        assert "Chunk Type: IEND" in captured.out
        assert "File size: 224566 bytes" in captured.out
