#!/usr/bin/python3

import tornado.web
import redis
import json
import keys
import shunlu_config
import FinishOrder
import RequireOpenID
from xml.etree.ElementTree import Element, tostring
import requests
import random
import hashlib

charset = "utf-8"

class PayService(object):
    def __init__(self):
        self.rds = redis.StrictRedis(shunlu_config.redis_ip, shunlu_config.redis_port)

    def gen_nonce_str(self):
        nonce_str = ''
        for index in range(32):
            current = random.randrange(0,62)
            if current < 10:
                temp = random.randint(0,9)
            elif current < 36:
                temp = chr(random.randint(65, 90))
            else:
                temp = chr(random.randint(97, 122))
            nonce_str += str(temp)
        return nonce_str

    def gen_md5(self, string):
        h1 = hashlib.md5()
        h1.update(string.encode(encoding='utf-8'))
        return h1.hexdigest()

    def gen_sign(self, order_dict):
        # WeChat Pay计算签名的算法
        # https://pay.weixin.qq.com/wiki/doc/api/wxa/wxa_api.php?chapter=4_3
        string_list = []
        for key, value in order_dict:
            if not value:
                continue
            else:
                string_list.append(str(key) + '=' + str(value))
        string_list.sort()
        string_a = ""
        for item in string_list:
            string_a += item
            string_a += "&"
        string_a += "key="
        string_a += shunlu_config.wc_pay_key
        sign = self.gen_md5(string_a).upper()
        return sign

    def dict_to_xml(self, tag, data_dict):
        '''turn a simple dict of key/value pairs into xml
        '''
        elem = Element(tag)
        for key, val in data_dict:
            child = Element(key)
            child.text = str(val)
            elem.append(child)
        return elem

    def prePay(self, wc_pay_url, body, out_trade_no, total_fee, spbill_create_ip, notify_url, openid):
        unifiedorder = {"appid":str(shunlu_config.appid),
                        "mch_id": str(shunlu_config.mch_id),
                        "nonce_str": str(self.gen_nonce_str()),
                        "body" : body,
                        "out_trade_no" : out_trade_no,
                        "total_fee" : int(total_fee*100),
                        "spbill_create_ip" : str(spbill_create_ip),
                        "notify_url" : notify_url,
                        "trade_type" : "JSAPI",
                        "openid" : str(openid),
                        }
        sign = self.gen_sign(unifiedorder)
        unifiedorder["sign"] = str(sign)
        xml_request = tostring(self.dict_to_xml("xml", unifiedorder), encoding="utf-8")
        pre_pay_request = requests.get(wc_pay_url, params=xml_request)




class OrderPayHandler(tornado.web.RequestHandler):
    service = PayService()

    def get(self):
        js_code = self.get_argument("jscode")
        iRet, openid, session_key = RequireOpenID.getOpenId(js_code)
        result = {}
        if iRet < 0:
            result["error_code"] = iRet
            self.set_header("Content-Type", "application/json; charset=UTF-8")
            self.write(json.dumps(result))
            return


