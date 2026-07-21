"""Test LLM Configuration"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.llm.parser import parse_design_params, LLMParseError, InputValidationError
from app.core.config import settings


async def test_llm():
    print("=" * 60)
    print("LLM Configuration Test")
    print("=" * 60)
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"LLM Provider: {settings.LLM_PROVIDER}")
    print(f"Tongyi API Key: {'[OK] Configured' if settings.TONGYI_API_KEY else '[EMPTY]'}")
    print(f"OpenAI API Key: {'[OK] Configured' if settings.OPENAI_API_KEY else '[EMPTY]'}")
    print("=" * 60)

    # Test input
    test_input = "送给妈妈的生日礼物，她属兔，喜欢月亮和桂花，希望是冷白釉，放玄关"
    print(f"\nTest Input: {test_input}")
    print("\nCalling LLM parser...\n")

    try:
        result = await parse_design_params(test_input, use_cache=False)
        print("[OK] Success! Parsed parameters:")
        print(f"  - 造型 (shape): {result.shape}")
        print(f"  - 釉色 (glaze_color): {result.glaze_color}")
        print(f"  - 尺寸 (size): {result.size}")
        print(f"  - 风格 (style): {result.style}")
        print(f"  - 情感 (emotion): {result.emotion}")
        print(f"  - 材质 (material): {result.material}")
        print(f"  - 用途 (usage): {result.usage}")
        print("\n" + "=" * 60)
        print("[OK] LLM is working correctly!")
        print("=" * 60)
        return True

    except InputValidationError as e:
        print(f"[ERROR] Input validation error: {e}")
        return False

    except LLMParseError as e:
        print(f"[ERROR] LLM API error: {e}")
        print("\nTroubleshooting:")
        if settings.LLM_PROVIDER == "tongyi" and not settings.TONGYI_API_KEY:
            print("  - Tongyi API Key is empty. Please set TONGYI_API_KEY in .env")
        elif settings.LLM_PROVIDER == "openai" and not settings.OPENAI_API_KEY:
            print("  - OpenAI API Key is empty. Please set OPENAI_API_KEY in .env")
        print("  - Check your API key is valid and has credits")
        print("  - Check your network connection")
        print("\n  If no API key is configured, the system will fall back to mock mode.")
        return False

    except Exception as e:
        print(f"[ERROR] Unexpected error: {type(e).__name__}: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_llm())
    sys.exit(0 if success else 1)
