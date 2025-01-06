import pytest
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from PNGParser.PNG import PNGParser


@pytest.fixture(scope="session")
def image_path():
    image_name = "cubes.png"
    return Path(__file__).parent / image_name


@pytest.fixture(scope="session")
def parser(image_path):
    """Shared parser instance for all tests"""
    return PNGParser(image_path)


@pytest.fixture(scope="session")
def parsed_data(parser):
    """Pre-parsed data for tests that need it"""
    data = parser.read_file()
    parser.parse_chunks(data)
    parser.process_chunks()
    return parser
