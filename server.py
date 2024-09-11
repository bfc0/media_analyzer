from aiohttp import web
import aiohttp
import anyio
import pymorphy2
from adapters.inosmi_ru import sanitize
from process_article import get_words_from_file, process_article, ProcessArticleContext, fetch

MAX_ARTICLES = 10


async def handle(request, context: ProcessArticleContext, limit=MAX_ARTICLES):
    raw_urls = request.query.get('url')
    if not raw_urls:
        raise web.HTTPBadRequest(
            text='{"error": "no urls in request"}', content_type="application/json")

    urls = raw_urls.split(',')
    if len(urls) > limit:
        raise web.HTTPBadRequest(
            text=f'{{"error": "too many urls in request, \
            should be {limit} or fewer"}}',
            content_type="application/json")

    stats = []
    async with aiohttp.ClientSession() as session:
        async with anyio.create_task_group() as tg:
            for url in urls:
                tg.start_soon(process_article,
                              url, stats, session, context)

    return web.json_response([stat.asdict() for stat in stats])

if __name__ == '__main__':
    words = get_words_from_file("dicts/positive_words.txt") \
        | get_words_from_file("dicts/negative_words.txt")

    context = ProcessArticleContext(
        morph=pymorphy2.MorphAnalyzer(),
        charged_words=words,
        fetch=fetch,
        sanitize=sanitize
    )

    app = web.Application()
    app.add_routes(
        [web.get('/', lambda request: handle(request, context=context))])
    web.run_app(app)
