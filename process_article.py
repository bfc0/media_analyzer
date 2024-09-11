import aiohttp
import asyncio
import adapters
import pymorphy2
import typing as t
from asyncio import timeout
from dataclasses import dataclass, asdict
from enum import Enum
from text_tools import calculate_jaundice_rate, split_by_words
from timer import Timer


DEFAULT_TIMEOUT = 1


@dataclass
class ProcessArticleContext:
    morph: pymorphy2.MorphAnalyzer
    charged_words: set[str]
    fetch: t.Callable[[aiohttp.ClientSession, str], str]
    sanitize: t.Callable[[str, bool], str]
    timeout: float = DEFAULT_TIMEOUT


class Status(Enum):
    OK = 1
    FETCH_ERROR = 2
    PARSE_ERROR = 3
    TIMED_OUT = 4


@dataclass
class ParseResult:
    url: str
    status: Status
    score: float | None = None
    words_count: int | None = None
    elapsed: str | None = None

    def __str__(self):
        if self.status == Status.OK:
            return (
                f"URL: {self.url}\n"
                f"Status: {self.status.name}\n"
                f"Score: {self.score}\n"
                f"Words: {self.words_count}\n"
                f"Parsed in {self.elapsed}\n"
            )

        return (
            f"URL: {self.url}\n"
            f"Status: {self.status.name}\n"
        )

    def asdict(self) -> dict[str, str | float | int | None]:
        data = asdict(self)
        data["status"] = self.status.name
        return data

    def without(self, attr: str) -> t.Self:
        if hasattr(self, attr):
            delattr(self, attr)
        return self


async def fetch(session: aiohttp.ClientSession, url: str) -> str:
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()


def get_words_from_file(filename: str) -> set[str]:
    with open(filename) as f:
        return set(f.read().split())


async def process_article(
        url: str,
        results: list[ParseResult],
        session: aiohttp.ClientSession,
        context: ProcessArticleContext,
) -> None:

    async with timeout(context.timeout):
        try:
            result = None
            text = await context.fetch(session, url)

            with Timer() as timer:
                santized_text = context.sanitize(text, plaintext=True)
                words = split_by_words(context.morph, santized_text)
                score = calculate_jaundice_rate(words, context.charged_words)

                result = ParseResult(
                    url=url,
                    status=Status.OK,
                    score=score,
                    words_count=len(words),
                    elapsed=timer.elapsed,
                )

        except aiohttp.ClientError:
            result = ParseResult(url=url, status=Status.FETCH_ERROR)

        except adapters.exceptions.ArticleNotFound:
            result = ParseResult(url=url, status=Status.PARSE_ERROR)

        except asyncio.CancelledError:
            result = ParseResult(url=url, status=Status.TIMED_OUT)

        finally:
            results.append(result)
