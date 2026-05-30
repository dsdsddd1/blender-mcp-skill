import argparse
import json
import urllib.error
import urllib.request


def request_json(method, url, payload=None, token=""):
    data = None
    headers = {
        "Content-Type": "application/json",
    }
    if token:
        headers["X-Bridge-Token"] = token
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Call the Blender collection deformer bridge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--token", default="")
    parser.add_argument("--collection", required=True)
    parser.add_argument("--host-object", default="RemoteCollectionDeformHost")
    parser.add_argument("--strength", type=float, default=0.35)
    parser.add_argument("--noise-scale", type=float, default=1.5)
    parser.add_argument("--translation", nargs=3, type=float, default=(0.0, 0.0, 0.0))
    parser.add_argument("--scale", nargs=3, type=float, default=(1.0, 1.0, 1.0))
    args = parser.parse_args()

    base_url = f"http://{args.host}:{args.port}"

    try:
        health = request_json("GET", f"{base_url}/health")
        print(json.dumps(health, ensure_ascii=False, indent=2))

        result = request_json(
            "POST",
            f"{base_url}/v1/collection-deformer",
            payload={
                "collection": args.collection,
                "host_object": args.host_object,
                "strength": args.strength,
                "noise_scale": args.noise_scale,
                "translation": list(args.translation),
                "scale": list(args.scale),
            },
            token=args.token,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {body}")
        raise SystemExit(1)
    except urllib.error.URLError as exc:
        print(f"Connection failed: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
