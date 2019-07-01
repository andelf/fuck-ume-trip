#!/usr/bin/env python3

import aiohttp
from aiohttp import web
import os.path
import logging
import api
import pb
import shelve
import aiosqlite
import json
from datetime import datetime


D = json.dumps

def fuck_addr(addr):
    addr = addr.replace('中国澳门', '澳门')
    addr = addr.replace('中国台北', '台湾台北')
    addr = addr.replace('中国香港', '香港')
    return addr

def flight_status_to_json(flight):
    return {
        'no': flight.flightNo,
        'aircorp': flight.airlineName,
        'status': flight.flightStatus,
        'std': flight.std,
        'sta': flight.sta,
        'atd': flight.atd,
        'ata': flight.ata,
        'etd': flight.etd,
        'eta': flight.eta,
        'dept': {
            'city': fuck_addr(flight.deptCity),
            'iata': flight.deptCityCode,
            'airport': fuck_addr(flight.deptAirportName),
            'terminal': flight.deptTerminal,
            'date': flight.deptFlightDate,
            'timezone': flight.deptTimeZone,
            'gate': flight.deptGate,
            'weather': flight.deptWeather,
            'temp': flight.deptTemp,
        },
        'dest': {
            'city': fuck_addr(flight.destCity),
            'iata': flight.destCityCode,
            'airport': fuck_addr(flight.destAirportName),
            'terminal': flight.destTerminal,
            'date': flight.destFlightDate,
            'timezone': flight.destTimeZone,
            'exit': flight.destExit,
            'weather': flight.destWeather,
            'temp': flight.destTemp
        },
        'plane': {
            'type': flight.planeType,
            'age': flight.planeAge,
            'no': flight.planeRegNo,
        },
        'hostFlight': {
            'no': flight.hostNos,
            'aircorp': flight.hostAirline,
            'desc': flight.hostFlightDesc,
        },
        'preFlight': {
            'no': flight.preFlightNo,
            'status': flight.preFlightStatus,
            'desc': flight.preFlightStatusDesc,
        }
    }



__db__ = "./umetrip.db"

def pb_to_error_json(reply):
    return {
            'error': {
                'code': reply.payload.errcode,
                'detail': reply.payload.errmsg or f'错误代码 {reply.payload.errcode}',
            }
        }

def error_json(code=233, detail="UNKNOWN"):
    return {
            'error': {
                'code': code,
                'detail': detail,
            }
        }



class ApiWrapper(object):
    def __init__(self, *args, **kwargs):
        self.api = api.Api()


    async def get_flight_status_by_code(self, code, date=''):
        date = date or datetime.now().strftime("%Y-%m-%d")
        code = str(code)
        reply = self.api.get_flight_status_by_code(code, date)
        self.api.randomize()
        print(reply)
        if reply.payload.errcode:
            return pb_to_error_json(reply)

        s2c = pb.S2cGetFlightStatusOrFlightList.FromString(reply.payload.responseBody)
        print(s2c)
        if not s2c.isSuccess:
            return error_json(detail=f'服务器直接返回错误，应该是远端没有这个数据了')

        if s2c.type == 0:
            flight_list = list(s2c.flightNoList)
            return error_json(detail=f"航班代码不唯一 {flight_list}")
        elif s2c.type == 1:
            if len(s2c.flightStatusList) == 1:
                flight = s2c.flightStatusList[0]
                return {
                    'data': flight_status_to_json(flight)
                }
            else:
                return error_json(detail=f'疑似代码共享航班')


    async def search_flight_no(self, code):
        code = str(code)
        if not code.isnumeric():
            return {
                'error': {
                    'code': 666,
                    'detail': '请使用数字搜索',
                }
            }
        async with aiosqlite.connect(__db__) as db:
            cursor = await db.execute('SELECT result FROM api_cache WHERE method=? AND parameter=?',
                ('search_flight_no', D({'code': code})))
            row = await cursor.fetchone()
            if row:
                print('hit cache')
                return json.loads(row[0])
            reply = self.api.get_flight_status_by_code(code)
            self.api.randomize()
            if reply.payload.errcode:
                print('! error', reply)
                return {
                    'error': {
                        'code': reply.payload.errcode,
                        'detail': reply.payload.errmsg or f'错误代码 {reply.payload.errcode}',
                    }
                }
            res = pb.S2cGetFlightStatusOrFlightList.FromString(reply.payload.responseBody)
            print(res)
            if res.type == 0:
                flight_list = list(res.flightNoList)
                ret = {'data': flight_list}
                await db.execute('INSERT INTO api_cache (method, parameter, result) VALUES (?, ?, ?)',
                    ('search_flight_no', D({'code': code}), D(ret)))
                await db.commit()
                return ret
            else:
                return {
                    'error': {
                        'code': 233,
                        'detail': '请求参数返回错误',
                    }
                }

async def handler(request):
    print(request)
    path = request.match_info.get('path', '')
    # path = request.rel_url

    stub = request.app['api_stub'] # ApiWrapper()

    if request.method == 'POST':
        print(path)
        if path == 'search_flights':
            req = await request.json()
            return web.json_response(await  stub.search_flight_no(req.get('code', '')))

        if path == 'get_flight_by_code':
            req = await request.json()
            return web.json_response(await stub.get_flight_status_by_code(**req))


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

    app['api_stub'] = ApiWrapper()

    app.add_routes([
        web.route('*', '/api/v1/{path:.*}', handler),
    #    web.route('*', '/static/{path:.*}', static_file_handler),
    ])
    app.router.add_static('/static/', path='./static/', name='static')
    app.router.add_get('/', index_handler)
    web.run_app(app, port=8443)


if __name__ == '__main__':
    main()
