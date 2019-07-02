#!/usr/bin/env python3

import base64
import requests
import uuid
# import time
from datetime import date, datetime

import aiohttp
from aiohttp import web

import pb
import umetrip
import json
import random


__headers__ = {
    'User-Agent': 'okhttp-okgo/jeasonlzy',
    'Accept-Language': 'en-US,en;q=0.8',
    'rcver': 'AND_a01_05.02.0528',
    # rpid: 1060044 => pid
    'rpver': '1.0',
    'Content-Serialize': '',  # or pb
    'Content-Type': 'application/octet-stream'
}


def random_uuid():
    return str(uuid.uuid4())

class RequestBuilder(object):
    def __init__(self, now=None, *args, **kwargs):
        self._now = now or datetime.now()
        self._pid = ''
        self._version = "1.0"
        self._data = {}
        self._key = ''
        self._uuid = ''
        self._last_req_time = f'{int(datetime.now().timestamp() * 1000)}'
        self._last_tid = ''
        self._page_id = ''
        self._name = ''

    def pid(self, pid):
        self._pid = pid
        return self

    def version(self, version):
        self._version = version
        return self

    def data(self, data):
        self._data = data
        return self

    def key(self, key):
        self._key = key
        return self

    def cuuid(self, cuuid):
        self._uuid = cuuid
        return self

    def last_req_time(self, tm):
        self._last_req_time = tm
        return self

    def last_tid(self, tid):
        self._last_tid = tid
        return self

    def page_id(self, pid):
        self._page_id = pid
        return self

    def name(self, rname):
        self._rname = rname
        return self



class PbRequest(RequestBuilder):

    def build_request_params(self, req):
        now = self._now
        req.rpver = (self._version or "1.0")
        req.rcver = "AND_a01_05.02.0528"
        req.rchannel = "10000000"  # be 10000000
        # req.rsid = ""
        # ???
        req.rcuuid = self._uuid

        if self._page_id:
            req.pageId = self._page_id

        assert self._pid
        req.rpid = self._pid
        req.rkey = now.strftime('%Y-%m-%d %H:%M:%S 8000')
        req.rsid = random_uuid()[:30] + self._key
        req.netType = "1"  # WiFi

        req.latitude = ""
        req.longitude = ""

        req.lastTransactionID = self._last_tid
        req.transactionID = \
            "{:>05.5s}{:>07s}{:.0f}".format(
                req.rcuuid, self._pid, now.timestamp() * 1000)

        req.lastReqTime = self._last_req_time

        # req.pageId
        if self._data:
            req.requestBody = self._data.SerializeToString()

        return req

    def build(self):
        if self._version and self._version >= '5.0':
            # use C2sBodyWrapPB
            req = pb.C2sBodyWrap()
            req = self.build_request_params(req)
            return req
        else:
            raise RuntimeError

class JObject(dict):
    def __getattr__(self, name):
        return self[name]
    def __setattr__(self, name, value):
        self[name] = value
        # return super().__setattr__(name, value)


class JsonRequest(RequestBuilder):
    def build(self):
        now = self._now

        tid = "{:>05.5s}{:>07s}{:.0f}".format(
            self._uuid, self._pid, now.timestamp() * 1000)
        # Use Json
        req = {
            "lastReqTime": self._last_tid,
            "latitude": "",
            "longitude": "",
            "netType": "1",
            # "pageId": "101003",
            "rchannel": "10000000",
            "rcuuid": self._uuid,
            "rcver": "AND_a01_05.02.0528",
            "rkey": now.strftime('%Y-%m-%d %H:%M:%S 8000'),
            "rparams": self._data,
            "rpid": self._pid,
            "rpver": self._version,
            "rsid": '',
            #            'pageId': '23333',
            "transactionID": tid,
            "lastTransactionID": self._last_tid,
        }
        if self._name:
            req['rname'] = self._name
        if self._page_id:
            req['pageId'] = self._page_id

        return req


def random_cuuid():
    return 'm' + ''.join(random.choice('0123456789abcdef') for _ in range(32))


class Api(object):
    def __init__(self, *args, **kwargs):
        # self._cuuid = "mc789fd2289a54f6b9757e9a6f66c256a"
        # self._cuuid = "mc789fd2189a54f6b9757e9a6f66c256a"
        self._cuuid = random_cuuid()
        self.last_tid = ""
        self.last_req_time = f'{int(datetime.now().timestamp() * 1000)}'

        self.sess = requests.session()

    def randomize(self):
        self._cuuid = random_cuuid()
        self.last_tid = ""
        self.last_req_time = f'{int(datetime.now().timestamp() * 1000)}'

    def request(self, req):
        use_pb = isinstance(req, PbRequest)

        URL = "http://ume1.umetrip.com/gateway/api/umetrip/native?encrypt=0"

        headers = __headers__.copy()
        headers.update({
            'rpid': req._pid,
            'rpver': req._version,
        })

        req = req \
            .cuuid(self._cuuid) \
            .last_tid(self.last_tid) \
            .last_req_time(self.last_req_time) \
            .build()

        if use_pb:
            headers['Content-Serialize'] = 'pb'
            self.last_tid = req.transactionID
            payload = req.SerializeToString()
            payload = base64.b64encode(payload)
        else:
            headers['Content-Serialize'] = ''
            self.last_tid = req['transactionID']
            payload = json.dumps(req)

        start_ts = datetime.now().timestamp()
        resp = self.sess.post(URL, payload, headers=headers)
        self.last_req_time = "%.0f" % (
            (datetime.now().timestamp() - start_ts) * 1000)

        if use_pb:
            reply = pb.CommonResponse.FromString(resp.content)
        else:
            reply = json.loads(resp.content, object_hook=JObject)

        return reply


    def get_key(self, s):
        tm = datetime.now().strftime("%Y-%m-%d").encode()
        return umetrip.sign(tm + s.encode()).decode()

    def get_flight_status_by_code(self, flight_no, dept_date=None, dept_iata='', dest_iata=''):
        dept_date = dept_date or datetime.now().strftime("%Y-%m-%d")
        payload = pb.C2sGetFlightStatusByCode(
            flightNo=flight_no,
            deptFlightDate=dept_date,
            deptAirportCode=dept_iata, # 用于多段航班
            destAirportCode=dest_iata,
        )
        print(payload)

        key = self.get_key(flight_no + dept_date)

        now = datetime.now()
        req = PbRequest(now) \
            .pid('1060029') \
            .version('5.0') \
            .key(key) \
            .data(payload)

        return self.request(req)

    def get_flight_status_by_city(self, dept_code, dest_code, dept_date=None):
        dept_date = dept_date or datetime.now().strftime("%Y%m%d")
        dept_date = dept_date.replace('-', '')
        # c2sSearchFlyByArea
        c2s = {
            'rstartcity': dept_code,
            'rendcity': dest_code,
            'rdate': dept_date
        }

        # getKey(3, this.d, new String[]{str, str2, str3});
        # 1, 2, 0
        key = self.get_key(dest_code + dept_date + dept_code)

        now = datetime.now()
        req = JsonRequest(now) \
            .pid("300028") \
            .version("1.0") \
            .key(key) \
            .data(c2s)

        return self.request(req)

    def update_data(self, ts=1561536854000, ts_new=1561536854000):
        c2s_startup = {
            'aircorpTimeStamp': ts,
            'airportTimeStamp': ts_new,
            'carcityTimeStamp': ts_new,
            'nationTimeStamp': ts_new,
            'sharedTimeStamp': ts_new,
        }
        now = datetime.now()
        req = JsonRequest(now) \
            .cuuid(self._cuuid) \
            .pid("1000013") \
            .version("1.0") \
            .data(c2s_startup)

        return self.request(req)

    def get_aircorp_list(self):
        req = JsonRequest() \
            .pid("100038") \
            .name("getaircorplist")
        return self.request(req)

    def get_airport_traffic_list(self, code='INC'):
        # c2sAirPortTrafficList
        c2s = {
            'rcode': code,
        }
        # not 100045
        req = JsonRequest() \
            .pid("100046") \
            .data(c2s)
        return self.request(req)

    def get_airport_traffic_detail(self, code='INC', linename='民航班车'):
        # c2sAirPortTrafficDetail
        c2s = {
            'rcode': code,
            'rlinename': linename,  # from get_airport_traffic_list
        }
        req = JsonRequest() \
            .pid("100051") \
            .data(c2s)
        return self.request(req)

    def get_airport_weather_info(self, code='HGH'):
        # c2sGetAirportWeatherInfo
        # 返回常为空。天气特情
        c2s = {
            'airPort': 'HGH',
            'index': 0,
        }
        req = JsonRequest() \
            .pid("1150001") \
            .data(c2s)
        return self.request(req)

    def get_airport_home(self, code='HGH'):
        # C2sAiportHome
        # 机场首页
        c2s = {
            'airPort': 'HGH',
            'screenWidth': '2160',
        }
        req = JsonRequest() \
            .pid("1030003") \
            .version("2.0") \
            .data(c2s)
        return self.request(req)

    def get_seatmap(self):
        # C2sEmptyCabinMap
        c2s = {
            'deptCode': 'KMG',
            'destCode': 'HGH',
            'flightDate': '2019-06-27',
            'flightNo': 'MU5646',
            'hostFlightNo': 'MU5646',
            'isBookSeatPage': False,
        }
        req = JsonRequest() \
            .pid("1402041") \
            .version("1.0") \
            .data(c2s)
        return self.request(req)

    def get_punctuality(self, code='MU5646', dept_date=None, dept_code='KMG', dest_code='HGH'):
        # s2cGetPunctualityRate
        # 有雷达图，航线
        dept_date = dept_date or datetime.now().strftime("%Y-%m-%d")
        c2s = {
            'flightNo': code,
            'depAirport': dept_code,
            'arrAirport': dest_code,
            'deptFlightDate': dept_date,
        }
        req = JsonRequest() \
            .pid("200367") \
            .page_id("106303") \
            .data(c2s)
        return self.request(req)

    def get_preflight_list(self, code='MU5646', reg_no='B7836', dept_date=None, dept_code='KMG', dest_code='HGH', std='MUST'):
        # c2sGetPreFlightList
        # api.get_preflight_list('MF8105', 'B7836', '2019-07-02', 'XMN', 'PEK', std='15:00')
        c2s = {
            'deptFlightDate': dept_date,
            'regNo': reg_no,
            'flightNo': code,
            'deptAirportCode': dept_code,
            'destAirportCode': dest_code,
            'std': std,
        }
        # 7: 2, 4, 1, 0, 3
        key = self.get_key(c2s['regNo'] + c2s['deptFlightDate'] + c2s['flightNo'] + c2s['deptAirportCode'] + c2s['std'])
        req = JsonRequest() \
            .pid("1060030") \
            .version("1.0") \
            .key(key) \
            .data(c2s)
        return self.request(req)


    def get_flight_status_link(self, code='MU5646', dept_date=None, dept_code='KMG', dest_code='HGH'):
        dept_date = dept_date or datetime.now().strftime("%Y-%m-%d")

        # 状态链 c2sFlightStatusLink
        c2s = {
            'deptFlightDate': '2019-06-27',
            'flightNo': 'MU5646',
            'deptAirportCode': 'KMG',
            'destAirportCode': 'HGH',
            'flightStatus': '',
        }
        req = JsonRequest() \
            .pid("1060037") \
            .data(c2s)
        return self.request(req)

    def get_perform_plane_info(self):
        # c2sPerformPlaneInfo
        c2s = {
            'flightdate': '2019-06-28',
            'regno': 'B6131',
            'adept': 'PEK',
            'adest': 'SHE',
            'flightno': 'CA1635',
        }
        req = JsonRequest() \
            .pid('1060042') \
            .data(c2s)
        return self.request(req)

    # API 可能会被禁掉？
    def get_aircorp_inout(self, code='PEK', page=0, status=""):
        # c2sAirportInOut, 查询机场动态信息
        c2s = {
            "airPort": code,
            "endTime": "",  # in format "16:00"
            "flightStatus": status,  # ['计划', '起飞', '到达', '预警', '延误', '取消', '备降', '返航']
            "isHost": False, # 是否只显示执飞
            "isInternational": 0,  # 0=NO, 1=YES, 2=ALL
            "isTomorrow": 0,
            "page": page,
            "startTime": "",
            "terminal": "",
            "type": 1
        }
        # 5: 0, 2, 1
        key = self.get_key(f'{c2s["airPort"]}{c2s["page"]}{c2s["type"]}')
        req = JsonRequest() \
            .pid('300351') \
            .key(key) \
            .version("2.0") \
            .data(c2s)
        return self.request(req)

    def get_aircorp_type_list(self, code='CA'):
        # get aircorp plane types
        req = JsonRequest() \
            .pid("100042") \
            .name("aircorptypelist") \
            .data({'rcode': code})
        return self.request(req)

    def get_aircorp_detail(self, code='CA'):
        req = JsonRequest() \
            .pid("100039") \
            .name("getaircorpdetail") \
            .data({'rcode': code})
        return self.request(req)

    def get_flight_pos(self, flight_no):
        # 当前位置
        #c2sGetFlightPosByFlightNoRuler
        req = JsonRequest() \
            .pid("1060026") \
            .data({'flightNo': flight_no})
        return self.request(req)


"""

req = JsonRequest() \
    .pid("200157") \
    .name("updateairports3") \
    .data({'ratimestamp': int(datetime.now().timestamp() * 1000) - 86400_000 * 100})
resp =  api.request(req)



# c2sGetFlightPathByRegionRuler
req = JsonRequest() \
    .pid("1060025") \
    .data({'longitude1': '103.952636', 'latitude1': '39.198205', 'longitude2': '109.116210', 'latitude2': '35.5143431'})
resp =  api.request(req)
resp
    """


if __name__ == '__main__':
    api = Api()
    resp = api.get_flight_status_by_code("4193")
    print(resp)

"""
flight_no = "4193"
dept_date = "2019-06-25"

resp = PbRequest() \
    .pid('1060029') \
    .version('5.0') \
    .key("") \
    .data(
        pb.C2sGetFlightStatusByCode(
            flightNo=flight_no,
            deptFlightDate=dept_date,
        )
    ).request()

raw =resp.content
print(reply)

api.get_flight_status_by_code('CA4192', '2019-06-26')

"""

# -10054 请求格式不对
# -10037
# -10035 freq?
