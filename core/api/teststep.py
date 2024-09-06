import datetime
import ssl
import sys
from time import sleep
from requests import request, Session
from copy import deepcopy
import json
from core.assertion import LMAssert
from core.api.websocket import WSClient
from tools.utils.sql import SQLConnect
from tools.utils.utils import extract, ExtractValueError, url_join, get_response_type, handle_variable_data
from urllib.parse import urlencode

REQUEST_CNAME_MAP = {
    'headers': '请求头',
    'proxies': '代理',
    'cookies': 'cookies',
    'params': '查询参数',
    'data': '请求体',
    'json': '请求体',
    'files': '上传文件'
}

SSL_OPT = {
    "cert_reqs": ssl.CERT_NONE,
    "check_hostname": False
}


class ApiTestStep:

    def __init__(self, test, session, collector, context, params):
        self.session = session
        self.collector = collector
        self.context = context
        self.params = params
        self.test = test
        self.status_code = None
        self.response_request = None
        self.response_headers = None
        self.response_content = None
        self.response_content_bytes = None
        self.response_cookies = None
        self.assert_result = None
        self.print = print
        self.message_queue = []

    def send_request(self):
        """http请求"""
        try:
            self.test.debugLog('[{}]接口执行开始'.format(self.collector.apiName))
            request_log = '【请求信息】:<br>'
            request_log += '{} {}<br>'.format(self.collector.method, url_join(self.collector.url, self.collector.path))
            for key, value in self.collector.others.items():
                if value is not None:
                    c_key = REQUEST_CNAME_MAP[key] if key in REQUEST_CNAME_MAP else key
                    if key == 'files':
                        if isinstance(value, dict):
                            request_log += '{}: {}<br>'.format(c_key, ["文件长度%s: %s" % (k, len(v)) for k,v in value.items()])
                        if isinstance(value, list):
                            request_log += '{}: {}<br>'.format(c_key, [i[1][0] for i in value])
                    elif c_key == '请求体':
                        request_log += '<span>{}: {}</span><br>'.format(c_key, dict2str(value))
                    else:
                        request_log += '{}: {}<br>'.format(c_key, dict2str(value))
            self.test.debugLog(request_log[:-4])
            url = url_join(self.collector.url, self.collector.path)
            self.test.recordTransDetail("method", self.collector.method)
            self.test.recordTransDetail("url", url if self.collector.others["params"] is None else "{}?{}".format(url, urlencode(self.collector.others["params"])))
            self.test.recordTransDetail("requestHeader", self.collector.others["headers"])
            if 'data' in self.collector.others:
                self.collector.body = self.collector.others['data']
            elif 'json' in self.collector.others:
                self.collector.body = self.collector.others['json']
            self.test.recordTransDetail("requestBody", self.collector.body)
            if self.collector.body_type == "form-urlencoded" and 'data' in self.collector.others:
                self.collector.others['data'] = urlencode(self.collector.others['data'])
            if self.collector.body_type in ("text", "xml", "html") and 'data' in self.collector.others:
                self.collector.others['data'] = str(self.collector.others['data']).encode("utf-8")
            if 'files' in self.collector.others and self.collector.others['files'] is not None:
                self.pop_content_type()
            if int(self.collector.controller["sleepBeforeRun"]) > 0:
                sleep(int(self.collector.controller["sleepBeforeRun"]))
                self.test.debugLog("请求前等待%sS" % int(self.collector.controller["sleepBeforeRun"]))
            start_time = datetime.datetime.now()
            if self.collector.controller["useSession"].lower() == 'true' and self.collector.controller["saveSession"].lower() == "true":
                res = self.session.session.request(self.collector.method, url, **self.collector.others)
            elif self.collector.controller["useSession"].lower() == "true":
                session = deepcopy(self.session.session)
                res = session.request(self.collector.method, url, **self.collector.others)
            elif self.collector.controller["saveSession"].lower() == "true":
                session = Session()
                res = session.request(self.collector.method, url, **self.collector.others)
                self.session.session = session
            else:
                res = request(self.collector.method, url, **self.collector.others)
            end_time = datetime.datetime.now()
            self.response_request = res.request
            self.test.recordTransDuring(int((end_time-start_time).microseconds/1000))
            self.save_response(res)
            response_log = '【响应信息】:<br>'
            response_log += '响应码: {}<br>'.format(self.status_code)
            response_log += '响应头: {}<br>'.format(dict2str(self.response_headers))
            self.test.recordTransDetail("method", res.request.method)
            self.test.recordTransDetail("url", res.request.url)
            self.test.recordTransDetail("requestHeader", dict(res.request.headers))
            self.test.recordTransDetail("requestBody", bytes2str(res.request.body, self.collector.body) if isinstance(res.request.body, bytes) else res.request.body)
            self.test.recordTransDetail("statusCode", self.status_code)
            self.test.recordTransDetail("responseHeader", self.response_headers)
            if 'content-disposition' not in [key.lower() for key in self.response_headers.keys()]:
                response_text = '<b>响应体: {}</b>'.format(dict2str(self.response_content))
                self.test.recordTransDetail("responseBody", self.response_content)
            else:
                response_text = '<b>响应体: 文件内容暂不展示, 长度{}</b>'.format(len(self.response_content_bytes))
                self.test.recordTransDetail("responseBody", "文件内容暂不展示, 长度{}".format(len(self.response_content_bytes)))
            response_log += response_text
            self.test.debugLog(response_log)
        finally:
            self.test.debugLog('[{}]接口执行结束'.format(self.collector.apiName))
            if int(self.collector.controller["sleepAfterRun"]) > 0:
                sleep(int(self.collector.controller["sleepAfterRun"]))
                self.test.debugLog("请求后等待%sS" % int(self.collector.controller["sleepAfterRun"]))

    def websocket_connect(self, websocket_infos, current_index):
        """websocket链接"""
        url = url_join(self.collector.url, self.collector.path)
        query = urlencode(self.collector.others["params"])
        msg_queue = None
        ws_name = self.collector.controller["saveWebsocket"]
        if ws_name is not None and ws_name != "":
            msg_queue = []
        headers = self.collector.others["headers"]
        if headers is not None and len(headers) == 0:
            headers = None
        ssl_opt = None
        if self.collector.others["verify"] is False:
            ssl_opt = SSL_OPT
        self.test.recordTransDetail("url", url+"?"+query)
        self.test.recordTransDetail("requestHeader", headers)
        try:
            request_log = '【链接信息】:<br>'
            request_log += '{}<br>'.format(url)
            request_log += '请求头：{}<br>'.format(self.collector.others["headers"])
            request_log += '查询参数：{}<br>'.format(self.collector.others["params"])
            self.test.debugLog(request_log[:-4])
            if int(self.collector.controller["sleepBeforeRun"]) > 0:
                sleep(int(self.collector.controller["sleepBeforeRun"]))
                self.test.debugLog("链接前等待%sS" % int(self.collector.controller["sleepBeforeRun"]))
            ws_connection = WSClient(self.test, current_index, url=url+"?"+query,
                                     msg_queue=msg_queue, ssl_options=ssl_opt, headers=headers)
            ws_connection.connect()
            self.test.recordTransDetail("responseBody", "Websocket链接成功")
            if int(self.collector.controller["sleepAfterRun"]) > 0:
                sleep(int(self.collector.controller["sleepAfterRun"]))
                self.test.debugLog("链接后等待%sS" % int(self.collector.controller["sleepAfterRun"]))
            if ws_name is not None:
                websocket_infos[ws_name] = {
                    "connection": ws_connection,
                    "messages": msg_queue
                }
            else:
                ws_connection.close_connection()
        except Exception as e:
            self.test.recordTransDetail("responseBody", "Websocket链接错误，错误信息：%s" % str(e))
            raise e

    def websocket_message(self, websocket_infos):
        """websocket发送消息"""
        self.test.debugLog('[{}]接口发送消息开始'.format(self.collector.apiName))
        try:
            if self.collector.apiName not in websocket_infos:
                raise Exception("{}链接不存在 请检查用例步骤".format(self.collector.apiName))
            ws_infos = websocket_infos[self.collector.apiName]
            self.message_queue = ws_infos["messages"]
            if self.collector.controller["clearMessageBefore"].lower() == "true":
                self.test.debugLog("请求前清空消息列表：%s" % str(ws_infos["messages"]))
                ws_infos["messages"].clear()
            self.test.recordTransDetail("requestBody", self.collector.message_text)
            if int(self.collector.controller["sleepBeforeRun"]) > 0:
                sleep(int(self.collector.controller["sleepBeforeRun"]))
                self.test.debugLog("发送前等待%sS" % int(self.collector.controller["sleepBeforeRun"]))
            self.test.debugLog('发送消息内容: {}'.format(self.collector.message_text))
            if self.collector.message_type == 'String': # 发送消息
                ws_infos["connection"].send(self.collector.message_text)
            else:
                ws_infos["connection"].send(self.collector.message_text.encode(), binary=True)
            if int(self.collector.controller["sleepAfterRun"]) > 0:
                sleep(int(self.collector.controller["sleepAfterRun"]))
                self.test.debugLog("发送后等待%sS" % int(self.collector.controller["sleepAfterRun"]))
            self.test.debugLog('接收消息内容:{}'.format(str(ws_infos["messages"])))
            self.test.recordTransDetail("responseBody", [str(message) for message in ws_infos["messages"]])
        finally:
            self.test.debugLog('[{}]接口发送消息完成'.format(self.collector.apiName))

    def looper_controller(self, case, api_list, step_n, current_index):
        """循环控制器"""
        if "type" in self.collector.looper and self.collector.looper["type"] == "WHILE":
            # while循环 且兼容之前只有for循环
            loop_start_time = datetime.datetime.now()
            index = 0
            self.test.recordTransDetail("type", "while")
            self.test.debugLog('[循环控制器]While循环执行开始, 循环条件:{}-{}-{}, 循环索引名:{}'.format(
                self.collector.looper["target"], self.collector.looper["assertion"],
                self.collector.looper["expect"], self.collector.looper["indexName"]))
            while self.collector.looper["timeout"] == 0 or (datetime.datetime.now() - loop_start_time).seconds * 1000 \
                    < self.collector.looper["timeout"]:     # timeout为0时可能会死循环 慎重选择
                if "indexName" in self.collector.looper and self.collector.looper["indexName"] != "":
                    self.test.recordVariableTrack(self.collector.looper["indexName"], index, "looper", self.context, index=current_index)
                    self.context[self.collector.looper["indexName"]] = index  # 给循环索引赋值第几次循环 母循环和子循环的索引名不应一样
                _looper = case.render_looper(self.collector.looper)  # 渲染循环控制控制器 每次循环都需要渲染
                index += 1
                result, msg = LMAssert(_looper['assertion'], _looper['target'], _looper['expect']).compare()
                if not result:
                    self.test.debugLog('[循环控制器]第{}次循环时不满足循环条件, 结束循环, 当前判断结果:{}'.format(index, msg), current_index)
                    break
                else:
                    self.test.debugLog('[循环控制器]第{}次循环时满足循环条件, 继续循环, 当前判断结果:{}'.format(index, msg), current_index)
                _api_list = api_list[step_n+1: (step_n + _looper["num"]+1)]
                case.loop_execute(_api_list, [], parent_index=current_index)
            else:
                self.test.debugLog('[循环控制器]当前循环超时, 结束循环', current_index)
        else:
            self.test.recordTransDetail("type", "for")
            # 渲染循环控制控制器 for只需渲染一次
            _looper = case.render_looper(self.collector.looper)
            self.test.debugLog('[循环控制器]for循环执行开始, 循环次数:{}, 循环索引名:{}'.format(_looper["times"], _looper["indexName"]))
            for index in range(_looper["times"]):  # 本次循环次数
                self.test.recordVariableTrack(self.collector.looper["indexName"], index, "looper", self.context, index=current_index)
                self.context[_looper["indexName"]] = index  # 给循环索引赋值第几次循环 母循环和子循环的索引名不应一样
                _api_list = api_list[step_n+1: (step_n + _looper["num"]+1)]
                case.loop_execute(_api_list, [], parent_index=current_index)
            else:
                self.test.debugLog('[循环控制器]当前循环完成, 结束循环', current_index)
        return self.collector.looper["num"]

    def condition_controller(self, case, api_list, step_n, current_index):
        """条件控制器"""
        self.test.recordTransDetail("type", "if")
        _conditions = case.render_conditions(self.collector.conditions["conditions"])
        offset_true = self.collector.conditions["trueNum"]
        offset_false = self.collector.conditions["falseNum"]
        final_result = True
        self.test.debugLog('[条件控制器]if条件执行开始')
        message = ""
        for condition in _conditions:
            try:
                result, msg = LMAssert(condition['assertion'], condition['target'], condition['expect']).compare()
                message = message + "<br>" + msg
                if not result:
                    final_result = False
            except Exception as e:
                self.test.errorLog('[条件控制器]条件判断错误, 错误信息: {}'.format(str(e)), current_index)
                final_result = False
        if final_result:
            self.test.recordTransDetail("result", True)
            self.test.debugLog('[条件控制器]条件判断为真, 执行True分支, 条件信息: {}'.format(message), current_index)
            skip_steps = [i for i in range(offset_true, offset_true + offset_false)]
        else:
            self.test.recordTransDetail("result", False)
            self.test.debugLog('[条件控制器]条件判断为假, 执行False分支, 条件信息: {}'.format(message), current_index)
            skip_steps = [i for i in range(0, offset_true)]
        _api_list = api_list[step_n + 1: (step_n + offset_true + offset_false + 1)]
        case.loop_execute(_api_list, skip_steps, parent_index=current_index)
        self.test.debugLog('[条件控制器]if条件执行结束', current_index)
        return offset_true+offset_false

    def variable_define(self, case, current_index):
        try:
            self.test.debugLog('[变量定义]定义变量开始')
            variables = self.collector.variables["data"]
            for variable in variables:
                if variable["type"] == 'JSONObject' or variable["type"] == 'JSONArray':
                    value = handle_variable_data(variable["type"], variable["value"])
                    final_value = case.render_variable(value)
                else:
                    value = case.render_variable(variable["value"])
                    final_value = handle_variable_data(variable["type"], value)
                self.test.recordVariableTrack(variable["name"], final_value, "variable", self.context, index=current_index)
                self.context[variable["name"]] = final_value
                self.test.debugLog(f'变量{variable["name"]}定义值为：{final_value}')
        finally:
            self.test.debugLog('[变量定义]定义变量结束')

    def exec_custom_script(self, case):
        try:
            self.test.debugLog('[自定义脚本]脚本执行开始')
            script = self.collector.script
            if script["type"] == "python":
                self.exec_script(script["code"])
            else:
                self.exec_sql(json.dumps(script["sql"]), case)
        finally:
            self.test.debugLog('[自定义脚本]脚本执行结束')

    def exec_script(self, code):
        """执行前后置脚本"""
        def print(*args, sep=' ', end='\n', file=None, flush=False):
            if file is None or file in (sys.stdout, sys.stderr):
                file = self.test.stdout_buffer
            self.print(*args, sep=sep, end=end, file=file, flush=flush)

        def sys_put(name, val, ps=False):
            if ps:  # 默认给关联参数赋值，只有多传入true时才会给公参赋值
                self.test.recordVariableTrack(name, val, "script", self.params, "common")
                self.params[name] = val
            else:
                self.test.recordVariableTrack(name, val, "script", self.context)
                self.context[name] = val

        def sys_get(name):
            if name in self.context:   # 优先从公参中取值
                return self.context[name]
            elif name in self.params:
                return self.params[name]
            else:
                raise KeyError("不存在的公共参数或关联变量: {}".format(name))

        names = locals()
        names["res_request"] = self.response_request
        names["res_code"] = self.status_code
        names["res_header"] = self.response_headers
        names["res_data"] = self.response_content
        names["res_cookies"] = self.response_cookies
        names["res_bytes"] = self.response_content_bytes
        try:
            exec(code)
            self.test.printOutput("python脚本执行成功")
        except Exception as e:
            self.test.printOutput("python脚本执行失败")
            raise e

    def exec_sql(self, sql, case):
        """执行前后置sql"""
        if sql == "{}":
            return
        sql = json.loads(case.render_sql(sql))
        if "host" not in sql["db"]:
            raise KeyError("获取数据库连接信息失败 请检查配置")
        conn = SQLConnect(**sql["db"])
        if sql["sqlType"] != "query":
            conn.exec(sql["sqlText"])
            self.test.printOutput("SQL更新成功, sql语句: {}".format(sql["sqlText"]))
        else:
            results = conn.query(sql["sqlText"])
            names = sql["names"].split(",")  # name数量可以比结果数量段，但不能长，不能会indexError
            self.test.printOutput("SQL查询成功, sql语句: {},\n 查询结果: {}".format(sql["sqlText"], results))
            for j, n in enumerate(names):
                if len(results) == 0:
                    self.test.recordVariableTrack(n, [], "sql", self.context)
                    self.context[n] = []    # 如果查询结果为空 则变量保存为空数组
                    continue
                if j >= len(results):
                    raise IndexError("变量数错误, 请检查变量数配置是否与查询语句一致，当前查询结果: <br>{}".format(results))
                self.test.recordVariableTrack(n, results[j], "sql", self.context)
                self.context[n] = results[j]  # 保存变量到变量空间

    def save_response(self, res):
        """保存响应结果"""
        self.status_code = res.status_code
        self.response_headers = dict(res.headers)
        self.response_content_bytes = res.content
        s = ''
        for key, value in res.cookies.items():
            s += '{}={};'.format(key, value)
        self.response_cookies = s[:-1]
        try:
            self.response_content = res.json()
        except Exception:
            self.response_content = res.text

    def extract_depend_params(self, case):
        """关联参数"""
        results = []
        if self.collector.relations is not None:
            relations = case.render_relations(self.collector.relations)
            try:
                for items in relations:
                    if items['expression'].strip() == '_RESPONSE_FILE':
                        value = self.response_content_bytes
                    elif items['expression'].strip() in ['_RESPONSE_COOKIE', '_RESPONSE_COOKIES']:
                        value = self.response_cookies
                    else:
                        if items['from'] == 'resHeader':
                            value = extract(items['method'], self.response_headers, items['expression'])
                        elif items['from'] == 'resBody':
                            value = extract(items['method'], self.response_content, items['expression'],
                                            get_response_type(self.response_headers))
                        elif items['from'] == 'resCookies':
                            value = self.response_cookies
                        elif items['from'] == 'reqHeader':
                            value = extract(items['method'], self.collector.others['headers'], items['expression'])
                        elif items['from'] == 'reqQuery':
                            value = extract(items['method'], self.collector.others['params'], items['expression'])
                        elif items['from'] == 'reqRest':
                            value = extract(items['method'], self.collector.rest, items['expression'])
                        elif items['from'] == 'reqBody':
                            value = extract(items['method'], self.collector.body, items['expression'], self.collector.body_type)
                        elif items['from'] == 'reqMessage':
                            value = extract(items['method'], self.collector.message_text, items['expression'])
                        elif items['from'] == 'resMessage':
                            value = extract(items['method'], self.message_queue, items['expression'])
                        else:
                            raise ExtractValueError('无法从{}位置提取依赖参数'.format(items['from']))
                    key = items['name']
                    self.test.recordVariableTrack(key, value, "relation", self.context)
                    self.context[key] = value
                    results.append([key, value])
            except ExtractValueError as e:
                self.test.recordTransDetail("relation", results)
                raise e
        self.test.recordTransDetail("relation", results)

    def check(self, case):
        """断言"""
        check_messages = list()
        if self.collector.assertions is not None:
            assertions = case.render_assertions(self.collector.assertions)
            results = list()
            results_detail = list()
            for items in assertions:
                try:
                    if items['from'] == 'resCode':
                        actual = self.status_code
                    elif items['from'] == 'resHeader':
                        actual = extract(items['method'], self.response_headers, items['expression'])
                    elif items['from'] == 'resBody':
                        actual = extract(items['method'], self.response_content, items['expression'],
                                         get_response_type(self.response_headers))
                    elif items['from'] == 'resCookies':
                        actual = extract(items['method'], self.response_cookies, items['expression'])
                    elif items['from'] == 'resMessage':
                        actual = extract(items['method'], self.message_queue, items['expression'])
                    elif items['from'] == 'database':
                        actual = extract(items['method'], None, items['expression'])
                    else:
                        raise ExtractValueError('无法在{}位置进行断言'.format(items['from']))
                    result, msg = LMAssert(items['assertion'], actual, items['expect']).compare()
                    results_detail.append([actual, items['assertion'], items['expect'], result, items['desc'] if 'desc' in items else ''])
                except ExtractValueError as e:
                    result = False
                    msg = '接口响应失败或{}'.format(str(e))
                results.append(result)
                check_messages.append(msg)
            self.test.recordTransDetail("assertion", results_detail)
            final_result = all(results)
        else:
            final_result, msg = LMAssert('相等', self.status_code, str(200)).compare()
            check_messages.append(msg)
        self.assert_result = {
            'apiId': self.collector.apiId,
            'apiName': self.collector.apiName,
            'result': final_result,
            'checkMessages': check_messages
        }

    def pop_content_type(self):
        if self.collector.others['headers'] is None:
            return
        pop_key = None
        for key, value in self.collector.others['headers'].items():
            if key.lower() == 'content-type':
                pop_key = key
                break
        if pop_key is not None:
            self.collector.others['headers'].pop(pop_key)


def dict2str(data):
    if not isinstance(data, str):
        return str(data)
    else:
        return data


def bytes2str(bytes_data:bytes, data):
    try:
        return bytes_data.decode("utf-8")
    except Exception:
        return data


class RemoveParamError(Exception):
    """参数移除错误"""


class AssertRelationError(Exception):
    """断言关系错误"""
