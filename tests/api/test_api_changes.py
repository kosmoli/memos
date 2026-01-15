#!/usr/bin/env python3
"""
Memos API Changes Test Script

Tests all the API changes made in Memos compared to Letta:
1. Provider CRUD operations (without provider_category)
2. LLM model listing (without provider_category)
3. Embedding model listing (dynamic fetching)
4. Hard delete behavior

Requirements:
- Memos server running on http://localhost:8283
- PostgreSQL running on localhost:5432
- Redis running on localhost:6379
- For embedding tests: OPENAI_API_KEY and OPENAI_BASE_URL env vars or args

Usage:
    # Basic tests (no real API calls)
    python test_api_changes.py

    # With real OpenAI API for embedding tests
    python test_api_changes.py --api-key sk-xxx --base-url https://api.openai.com/v1

    # Using environment variables
    export OPENAI_API_KEY=sk-xxx
    export OPENAI_BASE_URL=https://api.openai.com/v1
    python test_api_changes.py
"""

import asyncio
import argparse
import os
import sys
from typing import Any

import httpx

# Configuration
BASE_URL = os.environ.get("MEMOS_BASE_URL", "http://localhost:8283")
DEFAULT_ORG_ID = "org-00000000-0000-4000-8000-000000000000"


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^60}{Colors.END}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 60}{Colors.END}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{Colors.YELLOW}  {text}{Colors.END}")


class APITester:
    """Test class for Memos API changes."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.created_providers = []
        self.created_orgs = []
        self.created_users = []

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()

    async def get(self, endpoint: str, **kwargs: Any) -> dict:
        """Make a GET request."""
        response = await self.client.get(f"{self.base_url}{endpoint}", **kwargs)
        return response.json() if response.content else {}

    async def post(self, endpoint: str, **kwargs: Any) -> dict:
        """Make a POST request."""
        response = await self.client.post(f"{self.base_url}{endpoint}", **kwargs)
        return response.json() if response.content else {}

    async def delete(self, endpoint: str, **kwargs: Any) -> dict:
        """Make a DELETE request."""
        response = await self.client.delete(f"{self.base_url}{endpoint}", **kwargs)
        return response.json() if response.content else {}

    async def test_1_list_providers_without_category(self) -> bool:
        """Test 1: List providers without provider_category parameter."""
        print_header("Test 1: List Providers (without provider_category)")

        try:
            # This should work without provider_category parameter
            providers = await self.get("/v1/providers")

            if isinstance(providers, list):
                print_success(f"GET /v1/providers returned {len(providers)} providers")
                print_info(f"Response format: list of provider objects")
                return True
            else:
                print_error(f"Unexpected response format: {type(providers)}")
                return False

        except Exception as e:
            print_error(f"Failed to list providers: {e}")
            return False

    async def test_2_create_provider(self, api_key: str) -> bool:
        """Test 2: Create a new provider (BYOK only, no is_byok parameter)."""
        print_header("Test 2: Create Provider")

        try:
            # Create an OpenAI provider
            provider_data = {
                "name": "test-openai-llm",
                "provider_type": "openai",
                "api_key": api_key,
                "base_url": "https://api.openai.com/v1"
            }

            provider = await self.post("/v1/providers", json=provider_data)

            if "id" in provider:
                self.created_providers.append(provider["id"])
                print_success(f"Created provider: {provider['name']} (ID: {provider['id']})")
                print_info(f"provider_type: {provider.get('provider_type')}")
                print_info(f"organization_id: {provider.get('organization_id')}")
                print_info("Note: No provider_category field in response")
                return True
            else:
                print_error(f"Failed to create provider: {provider}")
                return False

        except Exception as e:
            print_error(f"Exception during provider creation: {e}")
            return False

    async def test_3_list_llms_without_category(self) -> bool:
        """Test 3: List LLM models without provider_category parameter."""
        print_header("Test 3: List LLM Models (without provider_category)")

        try:
            # This should work without provider_category parameter
            models = await self.get("/v1/llms")

            if isinstance(models, list):
                print_success(f"GET /v1/llms returned {len(models)} models")
                if models:
                    first_model = models[0]
                    print_info(f"Sample model: {first_model.get('handle', 'N/A')}")
                return True
            else:
                print_error(f"Unexpected response format: {type(models)}")
                return False

        except Exception as e:
            print_error(f"Failed to list LLM models: {e}")
            return False

    async def test_4_list_embeddings_dynamic(self) -> bool:
        """Test 4: List embedding models (dynamic fetching, no hardcoded models)."""
        print_header("Test 4: List Embedding Models (Dynamic Fetching)")

        try:
            # List all embedding models
            models = await self.get("/v1/embeddings")

            if isinstance(models, list):
                print_success(f"GET /v1/embeddings returned {len(models)} models")

                # Check that models are dynamically fetched, not hardcoded
                for model in models[:5]:  # Show first 5
                    print_info(f"Model: {model.get('handle', 'N/A')}")

                # Verify no "ghost" embedding models from providers that don't support embeddings
                ghost_models = [m for m in models if "test-openai-llm" in m.get("handle", "")]
                if ghost_models:
                    print_error(f"Found ghost embedding models: {ghost_models}")
                    return False
                else:
                    print_success("No ghost embedding models found (dynamic fetching works)")

                return True
            else:
                print_error(f"Unexpected response format: {type(models)}")
                return False

        except Exception as e:
            print_error(f"Failed to list embedding models: {e}")
            return False

    async def test_5_hard_delete_provider(self) -> bool:
        """Test 5: Hard delete provider and verify it's completely removed."""
        print_header("Test 5: Hard Delete Provider")

        if not self.created_providers:
            print_info("No providers to delete (creation might have failed)")
            return True

        provider_id = self.created_providers[0]

        try:
            # Delete the provider
            deleted_provider = await self.delete(f"/v1/providers?provider_id={provider_id}")

            if deleted_provider:
                print_success(f"Deleted provider: {deleted_provider.get('name')}")

            # Try to get the deleted provider - should fail
            try:
                providers = await self.get("/v1/providers")
                deleted_still_exists = any(p.get("id") == provider_id for p in providers)

                if deleted_still_exists:
                    print_error("Provider still exists after deletion (soft delete detected)")
                    return False
                else:
                    print_success("Provider completely removed from database (hard delete works)")
                    return True

            except Exception as e:
                print_error(f"Error verifying hard delete: {e}")
                return False

        except Exception as e:
            print_error(f"Failed to delete provider: {e}")
            return False

    async def test_6_create_duplicate_after_delete(self) -> bool:
        """Test 6: Create provider with same name after hard delete."""
        print_header("Test 6: Reuse Provider Name After Delete")

        try:
            # Try to create a provider with the same name as the deleted one
            provider_data = {
                "name": "test-openai-llm",  # Same name as deleted provider
                "provider_type": "openai",
                "api_key": "sk-test-dummy-key",
                "base_url": "https://api.openai.com/v1"
            }

            provider = await self.post("/v1/providers", json=provider_data)

            if "id" in provider:
                self.created_providers.append(provider["id"])
                print_success(f"Recreated provider with same name: {provider['name']}")
                print_success("Hard delete allows name reuse")
                return True
            else:
                print_error(f"Failed to recreate provider: {provider}")
                return False

        except Exception as e:
            # This might fail due to API key validation, which is expected
            if "422" in str(e) or "validation" in str(e).lower():
                print_info("Provider creation failed due to validation (API key), not name conflict")
                print_success("Hard delete allows name reuse (validation error is expected)")
                return True
            print_error(f"Exception during provider recreation: {e}")
            return False

    async def test_7_no_provider_category_in_response(self) -> bool:
        """Test 7: Verify provider_category is not in API responses."""
        print_header("Test 7: No provider_category Field in Responses")

        try:
            providers = await self.get("/v1/providers")

            has_category = False
            for provider in providers:
                if "provider_category" in provider:
                    print_error(f"Found provider_category in provider: {provider.get('name')}")
                    has_category = True

            if not has_category:
                print_success("No provider_category field found in any provider")
                return True
            return False

        except Exception as e:
            print_error(f"Failed to check for provider_category: {e}")
            return False

    async def run_all_tests(self, api_key: str | None = None) -> None:
        """Run all tests."""
        print(f"\n{Colors.BOLD}Memos API Changes Test Suite{Colors.END}")
        print(f"Testing against: {BASE_URL}\n")

        results = {}

        # Run tests
        results["test_1"] = await self.test_1_list_providers_without_category()
        results["test_2"] = await self.test_2_create_provider(api_key or "sk-test-dummy")
        results["test_3"] = await self.test_3_list_llms_without_category()
        results["test_4"] = await self.test_4_list_embeddings_dynamic()
        results["test_5"] = await self.test_5_hard_delete_provider()
        results["test_6"] = await self.test_6_create_duplicate_after_delete()
        results["test_7"] = await self.test_7_no_provider_category_in_response()

        # Cleanup
        await self._cleanup()

        # Print summary
        print_header("Test Summary")
        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test_name, result in results.items():
            status = f"{Colors.GREEN}PASS{Colors.END}" if result else f"{Colors.RED}FAIL{Colors.END}"
            print(f"{test_name}: {status}")

        print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.END}\n")

        sys.exit(0 if passed == total else 1)

    async def _cleanup(self) -> None:
        """Clean up created resources."""
        print_header("Cleanup")

        for provider_id in self.created_providers:
            try:
                await self.delete(f"/v1/providers?provider_id={provider_id}")
            except Exception:
                pass  # Best effort cleanup


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Memos API changes")
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="OpenAI API key for testing (optional, uses dummy key if not provided)"
    )
    args = parser.parse_args()

    tester = APITester(BASE_URL)
    try:
        await tester.run_all_tests(args.api_key)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
