import aiohttp
import asyncio
import argparse
import pymorphy2
from async_timeout import timeout
from enum import Enum
from dataclasses import dataclass
from anyio import create_task_group
import adapters
from adapters.inosmi_ru import sanitize
from text_tools import calculate_jaundice_rate, split_by_words

DEFAULT_TIMEOUT = 1
SAMPLE_ARTICLES = [
    "https://inosmi.ru/20240908/otpusk-270028360.html",
    "https://inosmi.ru/20240908/mvf-270028927.html",
    "https://inosmi.ru/20240908/pomidory-269986456.html",
    "https://inosmi.ru/20240907/mariytsy-270025800.html",
    "https://inosmi.ru/artarst/mariytsy-270025800.html",
    "https://www.rbc.ru/quote/news/article/66df01599a7947d2b245e922",
]


class Status(Enum):
    OK = 1
    FETCH_ERROR = 2
    PARSE_ERROR = 3
    TIMED_OUT = 4


@dataclass
class ParseResult:
    url: str
    status: Status
    score: float = 0
    words_count: int = 0

    def __str__(self):
        if self.status == Status.OK:
            return (
                f"URL: {self.url}\n"
                f"Status: {self.status.name}\n"
                f"Score: {self.score}\n"
                f"Words: {self.words_count}\n"
            )

        return (
            f"URL: {self.url}\n"
            f"Status: {self.status.name}\n"
        )


async def fetch(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


def get_words_from_file(filename: str) -> set[str]:
    with open(filename) as f:
        return set(f.read().split())


async def process_article(session, morph, charged_words, url,  results: list[ParseResult]) -> None:
    async with timeout(DEFAULT_TIMEOUT):
        try:

            result = None
            text = await fetch(session, url)
            santized_text = sanitize(text, plaintext=True)
            words = split_by_words(morph, santized_text)
            score = calculate_jaundice_rate(words, charged_words)

            result = ParseResult(
                url=url,
                status=Status.OK,
                score=score,
                words_count=len(words),
            )

        except aiohttp.ClientError:
            result = ParseResult(
                url=url,
                status=Status.FETCH_ERROR,
            )

        except adapters.exceptions.ArticleNotFound:
            result = ParseResult(
                url=url,
                status=Status.PARSE_ERROR,
            )

        except asyncio.CancelledError:
            result = ParseResult(
                url=url,
                status=Status.TIMED_OUT,
            )

        finally:
            results.append(result)


async def main():
    parser = argparse.ArgumentParser()
    # parser.add_argument('url', type=str)
    args = parser.parse_args()
    words = get_words_from_file(
        "dicts/positive_words.txt") | get_words_from_file("dicts/negative_words.txt")

    morph = pymorphy2.MorphAnalyzer()

    results = []
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in SAMPLE_ARTICLES:
                tg.start_soon(process_article, session,
                              morph, words, url,  results)

    for result in results:
        print(result)


asyncio.run(main())
