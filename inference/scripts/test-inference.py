#!/usr/bin/env python3
"""Phase 1 smoke test for Ollama + FastAPI inference."""

import sys
import argparse
import asyncio
import httpx
from typing import Dict, Any, List


class InferenceTester:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.passed = 0
        self.failed = 0
        
    async def test_health(self) -> bool:
        """Test: GET /health returns model status."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/health")
                if resp.status_code != 200:
                    print(f"FAIL: Health endpoint returned {resp.status_code}")
                    return False
                    
                data = resp.json()
                required_keys = ["status", "model", "ollama_reachable", "available_models"]
                missing = [k for k in required_keys if k not in data]
                if missing:
                    print(f"FAIL: Health missing keys: {missing}")
                    return False
                    
                if data.get("ollama_reachable") != True:
                    print(f"FAIL: Ollama not reachable")
                    return False
                    
                print("PASS: Health endpoint returns model status")
                return True
        except Exception as e:
            print(f"FAIL: Health test error: {e}")
            return False

    async def test_basic_completion(self) -> bool:
        """Test: POST /v1/chat/completions returns code completion."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": "mosdac-coder",
                        "messages": [
                            {"role": "user", "content": "Write a Python function that adds two numbers"}
                        ],
                        "max_tokens": 50,
                        "stream": False
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if resp.status_code != 200:
                    print(f"FAIL: Completion returned {resp.status_code}: {resp.text}")
                    return False
                    
                data = resp.json()
                if "choices" not in data or len(data["choices"]) == 0:
                    print("FAIL: No choices in response")
                    return False
                    
                content = data["choices"][0].get("message", {}).get("content", "")
                if not content:
                    print("FAIL: No content in response")
                    return False
                    
                if "usage" not in data:
                    print("FAIL: No usage object in response")
                    return False
                    
                usage = data["usage"]
                if "prompt_tokens" not in usage or "completion_tokens" not in usage:
                    print("FAIL: Usage missing token counts")
                    return False
                    
                print(f"PASS: Basic completion works (generated {usage['completion_tokens']} tokens)")
                return True
        except Exception as e:
            print(f"FAIL: Completion test error: {e}")
            return False

    async def test_streaming(self) -> bool:
        """Test: Streaming responses work correctly."""
        try:
            tokens_received = []
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": "mosdac-coder",
                        "messages": [{"role": "user", "content": "def hello(): pass"}],
                        "max_tokens": 30,
                        "stream": True
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"}
                ) as response:
                    
                    if response.status_code != 200:
                        print(f"FAIL: Streaming returned {response.status_code}")
                        return False
                        
                    async for line in response.aiter_lines():
                        if line.strip() and line.startswith("data:"):
                            tokens_received.append(line)
                            
            if len(tokens_received) == 0:
                print("FAIL: No streaming chunks received")
                return False
                
            # Check for final [DONE] marker
            has_done = any("[DONE]" in t for t in tokens_received)
            if not has_done:
                print("FAIL: No [DONE] marker in stream")
                return False
                
            print(f"PASS: Streaming works ({len(tokens_received)} chunks)")
            return True
        except Exception as e:
            print(f"FAIL: Streaming test error: {e}")
            return False

    async def test_max_tokens(self) -> bool:
        """Test: max_tokens parameter is enforced."""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": "mosdac-coder",
                        "messages": [{"role": "user", "content": "Count to 20: 1, 2, 3,"}],
                        "max_tokens": 10,
                        "stream": False
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                
                if resp.status_code != 200:
                    print(f"FAIL: max_tokens test returned {resp.status_code}")
                    return False
                    
                data = resp.json()
                usage = data.get("usage", {})
                completion_tokens = usage.get("completion_tokens", 0)
                
                # Allow small tolerance for tokenizer variance
                if completion_tokens > 12:
                    print(f"FAIL: max_tokens not enforced (got {completion_tokens}, max 10)")
                    return False
                    
                print(f"PASS: max_tokens enforced ({completion_tokens} tokens, max 10)")
                return True
        except Exception as e:
            print(f"FAIL: max_tokens test error: {e}")
            return False

    async def run_all_tests(self) -> bool:
        """Run all tests and report results."""
        print("=" * 50)
        print("Phase 1: Core Inference (RTX 1650) - Smoke Tests")
        print("=" * 50)
        
        # Test 1: Health
        print("\n[Test 1] Health Endpoint")
        if await self.test_health():
            self.passed += 1
        else:
            self.failed += 1
            
        # Test 2: Basic Completion
        print("\n[Test 2] Basic Code Completion")
        if await self.test_basic_completion():
            self.passed += 1
        else:
            self.failed += 1
            
        # Test 3: Streaming
        print("\n[Test 3] Streaming Responses")
        if await self.test_streaming():
            self.passed += 1
        else:
            self.failed += 1
            
        # Test 4: max_tokens
        print("\n[Test 4] max_tokens Enforcement")
        if await self.test_max_tokens():
            self.passed += 1
        else:
            self.failed += 1
            
        # Summary
        print("\n" + "=" * 50)
        print(f"Results: {self.passed} passed, {self.failed} failed")
        print("=" * 50)
        
        return self.failed == 0


async def main():
    parser = argparse.ArgumentParser(description="Phase 1 smoke tests")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--api-key", default="dev-key-123", help="API key")
    args = parser.parse_args()
    
    tester = InferenceTester(args.base_url, args.api_key)
    success = await tester.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())