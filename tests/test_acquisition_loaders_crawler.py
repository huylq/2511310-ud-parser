"""Offline: injects a fake `fetch` callable and fakes BronzeStore -- no real
HTTP request or live MinIO needed. The TokenBucket's real timing is exercised
via Task 4's own tests; here we only check crawl_source calls .acquire()
once per URL."""
import httpx

from vietnlp.acquisition.loaders.crawler import crawl_source
from vietnlp.acquisition.sources import SourceRecord


class _FakeBronzeStore:
    def __init__(self):
        self.records: list[dict] = []

    def put_record(self, record: dict) -> str:
        self.records.append(record)
        return f"bronze/fake/{len(self.records)}.parquet"


def _source(**overrides) -> SourceRecord:
    defaults = dict(
        id=1, name="test-forum", tier="forum_qa_blog", base_url="https://forum.example.vn",
        license="cc-by", robots_policy="allowed", enabled=True, rate_limit_seconds=5,
    )
    defaults.update(overrides)
    return SourceRecord(**defaults)


def _fake_fetch(responses: dict[str, httpx.Response]):
    def fetch(url: str) -> httpx.Response:
        return responses[url]
    return fetch


def test_crawls_every_seed_url():
    urls = ["https://forum.example.vn/thread/1", "https://forum.example.vn/thread/2"]
    responses = {u: httpx.Response(200, text=f"post body for {u}") for u in urls}
    bronze = _FakeBronzeStore()
    result = crawl_source(_source(), urls, bronze, fetch=_fake_fetch(responses))
    assert result == {"loaded": 2, "dead_lettered": 0}
    assert bronze.records[0]["raw_payload"] == b"post body for https://forum.example.vn/thread/1"


def test_dead_letters_a_non_200_response():
    urls = ["https://forum.example.vn/thread/gone"]
    responses = {urls[0]: httpx.Response(404, text="not found")}
    bronze = _FakeBronzeStore()
    result = crawl_source(_source(), urls, bronze, fetch=_fake_fetch(responses))
    assert result == {"loaded": 0, "dead_lettered": 1}


def test_dead_letters_empty_body():
    urls = ["https://forum.example.vn/thread/empty"]
    responses = {urls[0]: httpx.Response(200, text="")}
    bronze = _FakeBronzeStore()
    result = crawl_source(_source(), urls, bronze, fetch=_fake_fetch(responses))
    assert result == {"loaded": 0, "dead_lettered": 1}


def test_rejects_a_url_outside_source_domain():
    urls = ["https://not-vetted.example/thread/1"]
    bronze = _FakeBronzeStore()
    caught = []
    result = crawl_source(_source(), urls, bronze, fetch=_fake_fetch({}), dead_letter_sink=caught.append)
    assert result == {"loaded": 0, "dead_lettered": 1}
    assert "outside" in caught[0][1]


def test_paces_requests_through_a_token_bucket(monkeypatch):
    acquired = []
    import vietnlp.acquisition.loaders.crawler as crawler_module

    original_bucket_cls = crawler_module.TokenBucket

    class _TrackingBucket(original_bucket_cls):
        def acquire(self, **kwargs):
            acquired.append(True)
            return 0.0

    monkeypatch.setattr(crawler_module, "TokenBucket", _TrackingBucket)

    urls = ["https://forum.example.vn/thread/1", "https://forum.example.vn/thread/2"]
    responses = {u: httpx.Response(200, text="body") for u in urls}
    crawl_source(_source(), urls, _FakeBronzeStore(), fetch=_fake_fetch(responses))
    assert len(acquired) == 2  # once per URL, before each request
