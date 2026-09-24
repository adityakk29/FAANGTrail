import json

from faangtrail import complexity


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(
            {
                "output": [
                    {
                        "content": [
                            {"text": '{"time_complexity":"O(n)","space_complexity":"O(1)"}'}
                        ]
                    }
                ]
            }
        ).encode("utf-8")


def test_analyze_complexity_sends_minimal_json_request(monkeypatch) -> None:
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(complexity, "urlopen", fake_urlopen)
    result = complexity.analyze_complexity("def solve(values): return values", "Find a result", api_key="secret")

    assert result.time == "O(n)"
    assert result.space == "O(1)"
    request, timeout = requests[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert timeout == 30
    assert request.headers["Authorization"] == "Bearer secret"
    assert payload["max_output_tokens"] == 40
    assert "exactly these two string fields" in payload["input"]
    assert "Do not include markdown, explanations" in payload["input"]


def test_analyze_complexity_requires_a_key() -> None:
    try:
        complexity.analyze_complexity("def solve(): pass", "A problem", api_key="")
    except complexity.ComplexityError as error:
        assert "API key" in str(error)
    else:
        raise AssertionError("analysis accepted an empty API key")
