"""Tests for the tool implementations."""

import pytest

from app.tools.calculator import CalculatorTool
from app.tools.datetime_tool import DateTimeTool
from app.tools.file_reader import FileReaderTool
from app.tools.web_search import WebSearchTool
from app.tools.base import ToolResult


@pytest.mark.asyncio
class TestCalculatorTool:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.tool = CalculatorTool()

    async def test_basic_addition(self):
        result = await self.tool.call('{"expression": "2 + 2"}')
        assert result.success
        assert result.content == "4"

    async def test_order_of_operations(self):
        result = await self.tool.call('{"expression": "2 + 3 * 4"}')
        assert result.success
        assert result.content == "14"

    async def test_sqrt(self):
        result = await self.tool.call('{"expression": "sqrt(144)"}')
        assert result.success
        assert "12" in result.content

    async def test_missing_argument(self):
        result = await self.tool.call("{}")
        assert not result.success
        assert "expression" in result.error.lower() or "required" in result.error.lower()

    async def test_invalid_expression(self):
        result = await self.tool.call('{"expression": "print(123)"}')
        # 'print' is not in the safe namespace
        assert not result.success

    async def test_to_definition(self):
        definition = self.tool.to_definition()
        assert definition.function.name == "calculator"
        assert "expression" in definition.function.parameters["properties"]


@pytest.mark.asyncio
class TestDateTimeTool:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.tool = DateTimeTool()

    async def test_current_time(self):
        result = await self.tool.call('{}')
        assert result.success
        assert "Current date/time:" in result.content

    async def test_with_timezone(self):
        result = await self.tool.call('{"timezone": "UTC"}')
        assert result.success
        assert "Year:" in result.content


@pytest.mark.asyncio
class TestFileReaderTool:
    async def test_read_allowed_file(self, data_dir):
        tool = FileReaderTool(data_dir=data_dir)
        result = await tool.call('{"path": "sample.txt"}')
        assert result.success
        assert "Hello from the data directory" in result.content

    async def test_path_traversal_blocked(self, data_dir):
        tool = FileReaderTool(data_dir=data_dir)
        result = await tool.call('{"path": "../../../etc/passwd"}')
        assert not result.success
        assert "denied" in result.error.lower() or "outside" in result.error.lower()

    async def test_file_not_found(self, data_dir):
        tool = FileReaderTool(data_dir=data_dir)
        result = await tool.call('{"path": "nonexistent.txt"}')
        assert not result.success
        assert "not found" in result.error.lower()


@pytest.mark.asyncio
class TestWebSearchTool:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.tool = WebSearchTool()

    async def test_known_query(self):
        result = await self.tool.call('{"query": "What is the capital of France?"}')
        assert result.success
        assert "Paris" in result.content

    async def test_unknown_query(self):
        result = await self.tool.call('{"query": "xyzzy plugh something completely different"}')
        assert result.success
        assert "No specific" in result.content or "simulated" in result.content
