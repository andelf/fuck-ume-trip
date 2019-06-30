#!/usr/bin/env python3

import aiohttp
from aiohttp import web
import os.path
import logging
import api
import pb


async def handler(request):
    print(request)
    path = request.match_info.get('path', '')
    # path = request.rel_url
    
    entry = api.Api()

    if request.method == 'POST':
        print(path)
        if path == 'get_flight_by_code':
            res = await request.json()
            print(res)
            code = res.get('code', '')
            if code and len(code) > 2:
                reply = entry.get_flight_status_by_code(code)
                res = repl.payload.responseBody
                res = pb.S2cGetFlightStatusOrFlightList.FromString(res)
                print(res)

                

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
        web.route('*', '/api/v1/{path:.*}', handler),
    #    web.route('*', '/static/{path:.*}', static_file_handler),
    ])
    app.router.add_static('/static/', path='./static/', name='static')
    app.router.add_get('/', index_handler)
    web.run_app(app, port=8443)


if __name__ == '__main__':
    main()
