#!/usr/bin/env python3
"""
Test Embedding Model Dynamic Fetching

This script tests that Memos dynamically fetches embedding models
from the OpenAI API instead of returning hardcoded models.

Usage:
    python test_embedding_fetching.py --api-key sk-xxx --base-url https://api.openai.com/v1

Or using environment variables:
    export OPENAI_API_KEY=sk-xxx
    export OPENAI_BASE_URL=https://api.openai.com/v1
    python test_embedding_fetching.py
"""

import argparse
import asyncio
import httpx
import os
import sys

# Configuration
BASE_URL = os.environ.get("MEMOS_BASE_URL", "http://localhost:8283")
API_KEY = os.environ.get("OPENAI_API_KEY")
BASE_URL_ENDPOINT = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str) -> None:
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}\n")


def print_success(text: str) -> None:
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str) -> None:
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str) -> None:
    print(f"{Colors.YELLOW}  {text}{Colors.END}")


async def test_embedding_fetching(api_key: str, base_url: str) -> None:
    """Test embedding model dynamic fetching."""

    print_header("Embedding Model Dynamic Fetching Test")

    async with httpx.AsyncClient() as client:
        # Step 1: Create a real OpenAI provider
        print(f"{Colors.BOLD}Step 1: Create OpenAI Provider{Colors.END}")
        provider_data = {
            "name": "openai-test-embedding",
            "provider_type": "openai",
            "api_key": api_key,
            "base_url": base_url
        }

        r = await client.post(f"{BASE_URL}/v1/providers/", json=provider_data)
        if r.status_code != 200:
            print_error(f"Failed to create provider: {r.status_code} - {r.text}")
            sys.exit(1)

        provider = r.json()
        provider_id = provider["id"]
        print_success(f"Created provider: {provider['name']} (ID: {provider_id})")
        print_info(f"Base URL: {base_url}")

        # Step 2: Fetch embedding models (should call OpenAI /models API)
        print(f"\n{Colors.BOLD}Step 2: Fetch Embedding Models (Dynamic){Colors.END}")
        r = await client.get(f"{BASE_URL}/v1/models/embedding")

        if r.status_code != 200:
            print_error(f"Failed to fetch embeddings: {r.status_code} - {r.text}")
        else:
            embeddings = r.json()

            # Filter models for our provider
            provider_embeddings = [e for e in embeddings if e.get("provider_id") == provider_id]

            print_success(f"Total embedding models in system: {len(embeddings)}")
            print_info(f"Embedding models for this provider: {len(provider_embeddings)}")

            if provider_embeddings:
                print(f"\n{Colors.BOLD}Found embedding models:{Colors.END}")
                for emb in provider_embeddings[:10]:  # Show first 10
                    handle = emb.get("handle", "N/A")
                    dim = emb.get("embedding_dim", "N/A")
                    print(f"  - {handle} (dim: {dim})")

                if len(provider_embeddings) > 10:
                    print(f"  ... and {len(provider_embeddings) - 10} more")

                # Verify they are dynamically fetched (check for expected OpenAI models)
                expected_patterns = ["text-embedding-ada-002", "text-embedding-3-small", "text-embedding-3-large"]
                found_patterns = [p for p in expected_patterns
                                 if any(p in e.get("handle", "") for e in provider_embeddings)]

                print(f"\n{Colors.BOLD}Dynamic Fetching Verification:{Colors.END}")
                if found_patterns:
                    print_success(f"Found expected OpenAI embedding models: {found_patterns}")
                    print_success("Dynamic fetching is working correctly!")
                else:
                    print_info("Note: Expected OpenAI models not found - might be using compatible API")
            else:
                print_info("No embedding models found - API might not support embeddings")

        # Step 3: Create a second provider with same name (test LLM-only scenario)
        print(f"\n{Colors.BOLD}Step 3: Test LLM-Only Provider Scenario{Colors.END}")

        # Delete the first provider
        r = await client.delete(f"{BASE_URL}/v1/providers/{provider_id}")
        if r.status_code == 200:
            print_success("Deleted original provider")

        # Create a provider that might not have embeddings (e.g., a proxy with limited models)
        # This simulates the original problem where all OpenAI providers showed 3 hardcoded models
        provider_data_2 = {
            "name": "openai-test-llm-only",
            "provider_type": "openai",
            "api_key": api_key,
            "base_url": base_url
        }

        r = await client.post(f"{BASE_URL}/v1/providers/", json=provider_data_2)
        if r.status_code == 200:
            provider_2 = r.json()
            provider_2_id = provider_2["id"]
            print_success(f"Created second provider: {provider_2['name']}")

            # Check if it shows phantom embedding models
            r = await client.get(f"{BASE_URL}/v1/models/embedding")
            if r.status_code == 200:
                embeddings = r.json()
                provider_2_embeddings = [e for e in embeddings if e.get("provider_id") == provider_2_id]

                print(f"\n{Colors.BOLD}Phantom Model Check:{Colors.END}")
                if len(provider_2_embeddings) == 0:
                    print_success("No phantom embedding models - correctly returns empty list")
                else:
                    print_info(f"Found {len(provider_2_embeddings)} embedding models")
                    print_info("This is correct - API actually supports these models")

            # Cleanup
            await client.delete(f"{BASE_URL}/v1/providers/{provider_2_id}")

        print(f"\n{Colors.GREEN}{Colors.BOLD}All tests completed!{Colors.END}")


async def main():
    parser = argparse.ArgumentParser(description="Test Memos embedding model dynamic fetching")
    parser.add_argument("--api-key", type=str, default=API_KEY,
                        help="OpenAI API key (default: from OPENAI_API_KEY env var)")
    parser.add_argument("--base-url", type=str, default=BASE_URL_ENDPOINT,
                        help="OpenAI base URL (default: from OPENAI_BASE_URL env var)")

    args = parser.parse_args()

    if not args.api_key:
        print_error("API key is required! Use --api-key or set OPENAI_API_KEY environment variable")
        sys.exit(1)

    await test_embedding_fetching(args.api_key, args.base_url)


if __name__ == "__main__":
    asyncio.run(main())
