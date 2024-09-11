import aiohttp
import asyncio
import argparse
import pymorphy2
from anyio import create_task_group

from adapters.inosmi_ru import sanitize
from process_article import ProcessArticleContext, fetch, get_words_from_file, process_article

SAMPLE_ARTICLES = [
    "https://inosmi.ru/20240908/otpusk-270028360.html",
    "https://inosmi.ru/20240908/mvf-270028927.html",
    "https://inosmi.ru/20240908/pomidory-269986456.html",
    "https://inosmi.ru/20240907/mariytsy-270025800.html",
    "https://inosmi.ru/artarst/mariytsy-270025800.html",
    "https://www.rbc.ru/quote/news/article/66df01599a7947d2b245e922",
]


async def main():
    words = get_words_from_file(
        "dicts/positive_words.txt") | get_words_from_file("dicts/negative_words.txt")

    context = ProcessArticleContext(
        morph=pymorphy2.MorphAnalyzer(),
        charged_words=words,
        fetch=fetch,
        sanitize=sanitize
    )

    results = []
    async with aiohttp.ClientSession() as session:
        async with create_task_group() as tg:
            for url in SAMPLE_ARTICLES:
                tg.start_soon(process_article,
                              url, results, session, context)

    for result in results:
        print(result)


asyncio.run(main())
