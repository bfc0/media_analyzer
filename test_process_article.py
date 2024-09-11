import asyncio
import aiohttp
import pytest
import pymorphy2
from copy import copy
from adapters.exceptions import ArticleNotFound
from process_article import ProcessArticleContext, ParseResult, Status, process_article


@pytest.fixture
async def session():
    async with aiohttp.ClientSession() as session:
        yield session


async def fetch_sucess(*args, **kwargs):
    return "один два три четыре"


def fake_sanitize(text, plaintext=False):
    return text


base_context = ProcessArticleContext(
    morph=pymorphy2.MorphAnalyzer(),
    charged_words=set("один два три четыре".split()),
    fetch=fetch_sucess,
    sanitize=fake_sanitize,
    timeout=0.1
)


async def test_process_article_with_fetch_error(session):
    async def fetch_throws(*args, **kwargs):
        raise aiohttp.ClientError

    ctx = copy(base_context)
    ctx.fetch = fetch_throws
    results = []
    await process_article("url", results, session, ctx)
    assert results == [ParseResult(url="url", status=Status.FETCH_ERROR)]


async def test_process_article_with_parse_error(session):
    def sanitize_throws(text, plaintext=False):
        raise ArticleNotFound

    ctx = copy(base_context)
    ctx.sanitize = sanitize_throws
    results = []
    await process_article("url", results, session, ctx)
    assert results == [ParseResult(url="url", status=Status.PARSE_ERROR)]


async def test_process_article_with_timeout(session):
    async def fetch_times_out(*args, **kwargs):
        await asyncio.sleep(0.1)

    ctx = copy(base_context)
    ctx.fetch = fetch_times_out
    results = []
    await process_article("url", results, session, ctx)
    assert results == [ParseResult(url="url", status=Status.TIMED_OUT)]


async def test_process_article_with_100_score(session):
    ctx = copy(base_context)
    results = []
    await process_article("url", results, session, ctx)
    assert results[0].without("elapsed") == ParseResult(
        url='url', status=Status.OK, score=100.0, words_count=4
    )


async def test_process_article_with_50_score(session):
    async def fetch_half(*args, **kwargs):
        return "один два три четыре пять шесть семь восемь"

    ctx = copy(base_context)
    ctx.fetch = fetch_half
    results = []
    await process_article("url", results, session, ctx)
    assert results[0].without("elapsed") == ParseResult(
        url='url', status=Status.OK, score=50.0, words_count=8
    )
