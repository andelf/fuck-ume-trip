#!/usr/bin/env python3



import aiohttp
from aiohttp import web
import os.path
import logging


async def handler(request):
    print(request)
    # path = request.match_info.get('path', '')
    path = request.rel_url
    base = 'https://gateway.shouqiev.com:8443'
    url = base + str(path)
    #proxy = 'http://127.0.0.1:1087'
    proxy =  None
    headers = dict(request.headers)

    headers['Host'] = 'gateway.shouqiev.com:8443'
    headers['Accept-Encoding'] = 'identity' # FIX chunked
    print(headers)
    async with aiohttp.ClientSession() as sess:
        if request.method == 'GET':
            async with sess.get(url, proxy=proxy, headers=headers) as resp:
                headers = resp.headers
                ret = web.StreamResponse()
                ret.headers.update(headers)
                await ret.prepare(request)
                async for data in resp.content.iter_any():
                    await ret.write(data)
                await ret.write_eof()
                return ret
        elif request.method == 'POST':
            body = await request.content.read()
            print(body)
            async with sess.post(url, data=body, proxy=proxy, headers=headers) as resp:
                headers = resp.headers
                print('RESP', headers)
                ret = web.StreamResponse()
                ret.headers.update(headers)
                await ret.prepare(request)
                async for data in resp.content.iter_any():
                    print('RESP', data)
                    await ret.write(data)
                await ret.write_eof()
                return ret


async def index_handler(request):
    return web.FileResponse('./index.html')



def main():
    logging.basicConfig()


    app = web.Application()
    app.add_routes([
        web.route('*', '/api/{path:.*}', handler),
    #    web.route('*', '/static/{path:.*}', static_file_handler),
    ])
    app.router.add_static('/static/', path='./static/', name='static')
    app.router.add_get('/', index_handler)
    web.run_app(app, port=8443)


if __name__ == '__main__':
    main()
