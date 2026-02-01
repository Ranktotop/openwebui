#!/usr/bin/env python3
"""
Test script for GPT-Researcher Queue Server
Tests the queue functionality with multiple concurrent requests
"""
import asyncio
import json
import websockets
from datetime import datetime


async def test_research_request(client_id: int, query: str, delay: float = 0):
    """
    Send a research request to the queue server

    Args:
        client_id: Unique identifier for this client
        query: Research query to send
        delay: Delay before sending request (for staggered testing)
    """
    if delay > 0:
        await asyncio.sleep(delay)

    uri = "ws://localhost:8001/ws"
    print(f"\n[Client {client_id}] Connecting to {uri}...")

    try:
        async with websockets.connect(uri) as websocket:
            # Send research request
            request = {
                "task": query,
                "report_type": "research_report",
                "report_source": "web",
                "tone": "Objective",
                "verbose": True
            }

            print(f"[Client {client_id}] Sending request: {query[:50]}...")
            await websocket.send(json.dumps(request))

            # Receive messages
            print(f"[Client {client_id}] Waiting for responses...")
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get('type', 'unknown')
                content = data.get('content', '')

                timestamp = datetime.now().strftime('%H:%M:%S')

                if msg_type == 'logs':
                    print(f"[Client {client_id}] [{timestamp}] LOG: {content[:100]}")
                elif msg_type == 'path':
                    print(f"[Client {client_id}] [{timestamp}] PATH: {content[:100]}")
                elif msg_type == 'report':
                    print(f"\n[Client {client_id}] [{timestamp}] ✅ REPORT RECEIVED!")
                    print(f"[Client {client_id}] Report length: {len(content)} chars")
                    sources = data.get('metadata', {}).get('sources', [])
                    print(f"[Client {client_id}] Sources: {len(sources)}")
                    break
                elif msg_type == 'error':
                    print(f"[Client {client_id}] [{timestamp}] ❌ ERROR: {content}")
                    break
                else:
                    print(f"[Client {client_id}] [{timestamp}] {msg_type.upper()}: {str(data)[:100]}")

    except Exception as e:
        print(f"[Client {client_id}] ❌ Exception: {e}")


async def test_queue_status():
    """Test the queue status endpoint"""
    import aiohttp

    print("\n" + "="*60)
    print("Testing Queue Status Endpoint")
    print("="*60)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8001/status') as response:
                data = await response.json()
                print(f"\nQueue Status:")
                print(f"  - Queue Size: {data['queue_size']}")
                print(f"  - Active Tasks: {data['active_tasks']}")
                print(f"  - Max Concurrent: {data['max_concurrent']}")
                print(f"  - Available Slots: {data['available_slots']}")
    except Exception as e:
        print(f"❌ Error checking status: {e}")


async def test_single_request():
    """Test a single research request"""
    print("\n" + "="*60)
    print("TEST 1: Single Research Request")
    print("="*60)

    await test_research_request(
        client_id=1,
        query="What are the latest developments in quantum computing?"
    )

    await asyncio.sleep(2)
    await test_queue_status()


async def test_queue_behavior():
    """Test queue behavior with multiple concurrent requests"""
    print("\n" + "="*60)
    print("TEST 2: Queue Behavior (2 simultaneous requests)")
    print("="*60)
    print("\nExpected behavior:")
    print("  - Client 1: Starts immediately")
    print("  - Client 2: Waits in queue (max concurrent = 1)")
    print("  - Client 2: Starts after Client 1 finishes")
    print()

    # Start two requests simultaneously
    await asyncio.gather(
        test_research_request(1, "Why is the sky blue?", delay=0),
        test_research_request(2, "How does photosynthesis work?", delay=0.5)
    )

    await asyncio.sleep(2)
    await test_queue_status()


async def test_health_check():
    """Test the health check endpoint"""
    import aiohttp

    print("\n" + "="*60)
    print("Testing Health Check Endpoint")
    print("="*60)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('http://localhost:8001/') as response:
                data = await response.json()
                print(f"\nHealth Check Response:")
                for key, value in data.items():
                    print(f"  - {key}: {value}")
    except Exception as e:
        print(f"❌ Error checking health: {e}")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("GPT-Researcher Queue Server Test Suite")
    print("="*60)
    print("\nMake sure:")
    print("  1. Queue Server is running on localhost:8001")
    print("  2. GPT-Researcher is running on localhost:8000")
    print()
    input("Press Enter to start tests...")

    # Health check
    await test_health_check()

    # Status check
    await test_queue_status()

    # Single request test
    # await test_single_request()

    # Queue behavior test
    # await test_queue_behavior()

    print("\n" + "="*60)
    print("Tests completed!")
    print("="*60)


if __name__ == "__main__":
    # Note: You need to install aiohttp for HTTP tests
    # pip install aiohttp
    try:
        import aiohttp
    except ImportError:
        print("⚠️  Warning: aiohttp not installed. Some tests will fail.")
        print("Install with: pip install aiohttp")

    asyncio.run(main())
