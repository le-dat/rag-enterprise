import argparse
import sys
from qdrant_client import QdrantClient
from src.config import settings

def print_collection_points(collection_name: str, limit: int) -> None:
    url = settings.QDRANT_URL
    api_key = settings.QDRANT_API_KEY
    
    if not url:
        print("❌ QDRANT_URL is not configured in settings.")
        sys.exit(1)
        
    client = QdrantClient(url=url, api_key=api_key)
    
    try:
        # Scroll points to see payload information
        results, _ = client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        print(f"\n=== Recent Points in Collection: '{collection_name}' (Limit: {limit}) ===")
        if not results:
            print("No points found or collection is empty.")
            return
            
        for idx, point in enumerate(results):
            print(f"\nPoint #{idx + 1}")
            print(f"  ID: {point.id}")
            print(f"  Payload:")
            for key, val in point.payload.items():
                # Clip text value if it is too long for easy reading
                if key == "text" and len(str(val)) > 150:
                    val = str(val)[:150] + "..."
                print(f"    {key}: {val}")
        print("=================================================================\n")
        
    except Exception as e:
        print(f"❌ Failed to fetch points from collection '{collection_name}': {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug collection payloads")
    parser.add_argument("--collection", default=settings.QDRANT_COLLECTION, help="Qdrant collection name")
    parser.add_argument("--limit", type=int, default=3, help="Number of points to print")
    
    args = parser.parse_args()
    print_collection_points(args.collection, args.limit)
