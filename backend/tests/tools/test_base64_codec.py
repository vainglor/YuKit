import pytest

from app.tools.base64_codec import Base64CodecInput, Base64CodecOptions, Base64CodecTool


@pytest.mark.asyncio
async def test_base64_codec_encodes_text() -> None:
    tool = Base64CodecTool()

    result = await tool.run(
        Base64CodecInput(text="Hello, YuKit"),
        Base64CodecOptions(mode="encode", charset="utf-8"),
    )

    assert result.text == "SGVsbG8sIFl1S2l0"
    assert result.size_bytes == len(result.text.encode("utf-8"))


@pytest.mark.asyncio
async def test_base64_codec_decodes_text() -> None:
    tool = Base64CodecTool()

    result = await tool.run(
        Base64CodecInput(text="5L2g5aW977yMWXVLaXQ="),
        Base64CodecOptions(mode="decode", charset="utf-8"),
    )

    assert result.text == "你好，YuKit"
    assert result.size_bytes == len(result.text.encode("utf-8"))


@pytest.mark.asyncio
async def test_base64_codec_rejects_invalid_base64() -> None:
    tool = Base64CodecTool()

    with pytest.raises(ValueError) as exc_info:
        await tool.run(Base64CodecInput(text="not base64!?"), Base64CodecOptions(mode="decode"))

    assert "Invalid Base64 input" in str(exc_info.value)
