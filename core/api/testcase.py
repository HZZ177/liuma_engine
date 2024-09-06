import re
import sys
from core.api.collector import ApiRequestCollector
from core.template import Template
from core.api.teststep import ApiTestStep, dict2str
from jsonpath_ng.parser import JsonPathParser
from tools.utils.utils import get_case_message, get_json_relation, handle_params_data, handle_api_path


class ApiTestCase:

    def __init__(self, test):
        self.test = test
        self.case_message = get_case_message(test.test_data)
        self.session = test.session
        self.context = test.context
        self.id = self.case_message['caseId']
        self.name = self.case_message['caseName']
        setattr(test, 'test_case_name', self.case_message['caseName'])
        setattr(test, 'test_case_desc', self.case_message['comment'])
        self.functions = self.case_message['functions']
        self.params = handle_params_data(self.test, self.case_message['params'])
        self.template = Template(self.test, self.context, self.functions, self.params)
        self.json_path_parser = JsonPathParser()
        self.websocket_infos = {}
        self.comp = re.compile(r"\{\{.*?\}\}")
        self.current_index = 0

    def execute(self):
        """用例执行入口函数"""
        if self.case_message['apiList'] is None:
            raise RuntimeError("无法获取API相关数据, 请重试!!!")
        try:
            self.loop_execute(self.case_message['apiList'], [])
        finally:
            for ws_info in self.websocket_infos.values():
                ws = ws_info["connection"]
                try:
                    ws.close_connection()
                except:
                    continue

    def loop_execute(self, api_list, skip_steps, step_n=0, parent_index=0):
        """循环执行"""
        while step_n < len(api_list):
            self.current_index += 1
            api_data = api_list[step_n]
            # 定义收集器
            collector = ApiRequestCollector()
            step = ApiTestStep(self.test, self.session, collector, self.context, self.params)
            # 定义事务
            self.test.defineTrans(api_data['apiId'], api_data['apiName'], self.current_index, parent_index,
                                  api_data['path'] if api_data['apiId'] != 'message' else api_data["body"]["text"],
                                  api_data['apiDesc'])
            # 收集步骤信息
            step.collector.collect(api_data)
            if step_n in skip_steps:     # if或else分支被跳过
                self.test.updateTransStatus(3)
                if step.collector.apiId == "looper":
                    self.test.recordTransDetail("looper", step.collector.looper)
                elif step.collector.apiId == "condition":
                    self.test.recordTransDetail("condition", step.collector.conditions)
                self.test.debugLog('[{}]步骤在条件控制之外不被执行'.format(api_data['apiName']))
                step_n += 1
                continue
            try:
                if step.collector.apiId == "looper":
                    looper_step_num = step.looper_controller(self, api_list, step_n, self.current_index)
                    step_n += looper_step_num + 1
                elif step.collector.apiId == "condition":
                    condition_step_num = step.condition_controller(self, api_list, step_n, self.current_index)
                    step_n += condition_step_num + 1
                elif step.collector.apiId == "variable":
                    step.variable_define(self, self.current_index)
                    step_n += 1
                elif step.collector.apiId == "script":
                    step.exec_custom_script(self)
                    step_n += 1
                else:
                    # 执行前置脚本和sql
                    if step.collector.controller["pre"] is not None:
                        for pre in step.collector.controller["pre"]:
                            if pre['name'] == 'preScript':
                                step.exec_script(pre["value"])
                            elif pre['name'] == 'preSql':
                                step.exec_sql(pre["value"], self)
                            else:
                                step.exec_mongo(pre["value"], self)
                    if step.collector.apiId == "message":
                        # 渲染信息
                        step.collector.message_text = self.render_message(step.collector.message_text)
                        step.websocket_message(self.websocket_infos)
                    else:
                        # 渲染主体
                        self.render_content(step)
                        if step.collector.protocol == 'HTTP':
                            step.send_request()
                        else:
                            step.websocket_connect(self.websocket_infos, self.current_index)
                    if step.collector.apiId == "message" or step.collector.protocol == 'HTTP':
                        # 关联参数
                        step.extract_depend_params(self)
                    # 执行后置脚本和sql
                    if step.collector.controller["post"] is not None:
                        for post in step.collector.controller["post"]:
                            if post['name'] == 'postScript':
                                step.exec_script(post["value"])
                            elif post['name'] == 'postSql':
                                step.exec_sql(post["value"], self)
                            else:
                                step.exec_mongo(post["value"], self)
                    if step.collector.apiId == "message" or step.collector.protocol == 'HTTP':
                        # 断言
                        step.check(self)
                        # 检查step的断言结果
                        if step.assert_result['result']:
                            self.test.debugLog('[{}]接口断言成功: {}'.format(step.collector.apiName,
                                                                           dict2str(step.assert_result['checkMessages'])))
                        else:
                            self.test.errorLog('[{}]接口断言失败: {}'.format(step.collector.apiName,
                                                                           dict2str(step.assert_result['checkMessages'])))
                            raise AssertionError(dict2str(step.assert_result['checkMessages']))
                    step_n += 1
            except Exception as e:
                error_info = sys.exc_info()
                if collector.apiId not in ("looper", "condition", "variable", "script") \
                        and collector.controller["errorContinue"].lower() == "true":
                    # 失败后继续执行
                    if issubclass(error_info[0], AssertionError):
                        self.test.recordFailStatus(error_info)
                    else:
                        self.test.recordErrorStatus(error_info)
                    step_n += 1
                else:
                    raise e

    def render_looper(self, looper):
        self.template.init(looper)
        _looper = self.template.render()
        if "times" in _looper:
            try:
                times = int(_looper["times"])
            except:
                times = 1
            _looper["times"] = times
        return _looper

    def render_conditions(self, conditions):
        self.template.init(conditions)
        return self.template.render()

    def render_sql(self, sql):
        self.template.init(sql)
        return self.template.render()

    def render_variable(self, data):
        self.template.init(data)
        return self.template.render()

    def render_message(self, message):
        self.template.init(message )
        return self.template.render()

    def render_assertions(self, assertions):
        self.template.init(assertions)
        return self.template.render()

    def render_relations(self, relations):
        self.template.init(relations)
        return self.template.render()

    def render_content(self, step):
        self.template.init(step.collector.url)
        step.collector.url = self.template.render()
        self.template.init(step.collector.path)
        step.collector.path = self.template.render()
        if step.collector.rest is not None:
            self.template.init(step.collector.rest)
            step.collector.rest = self.template.render()
            step.collector.path = handle_api_path(step.collector.path, step.collector.rest)
        if step.collector.others.get('headers') is not None:
            headers = step.collector.others.pop('headers')
        else:
            headers = None
        if step.collector.others.get('params') is not None:
            query = step.collector.others.pop('params')
        else:
            query = None
        if step.collector.others.get('data') is not None:
            body = step.collector.others.pop('data')
            pop_key = 'data'
        elif step.collector.others.get('json') is not None:
            body = step.collector.others.pop('json')
            pop_key = 'json'
        else:
            body = None
            pop_key = None
        files = None
        if "files" in step.collector.others:
            files = step.collector.others.pop("files")
        self.template.init(step.collector.others)
        step.collector.others = self.template.render()
        self.template.set_help_data(step.collector.url, step.collector.path, headers, query, body)
        if files:
            step.collector.others["files"] = files
        if "#{_request_query" in str(headers).lower() or "#{_request_body" in str(headers).lower():
            if "#{_request_body" in str(query).lower():
                self.render_json(step, body, "body", pop_key)
                self.render_json(step, query, "query")
                self.render_json(step, headers, "headers")
            else:
                self.render_json(step, query, "query")
                self.render_json(step, body, "body", pop_key)
                self.render_json(step, headers, "headers")
        else:
            if "#{_request_body" in str(query).lower():
                self.render_json(step, headers, "headers")
                self.render_json(step, body, "body", pop_key)
                self.render_json(step, query, "query")
            else:
                self.render_json(step, headers, "headers")
                self.render_json(step, query, "query")
                self.render_json(step, body, "body", pop_key)

    def render_json(self, step, data, name, pop_key=None):
        if data is None:
            return
        if name == "body" and step.collector.body_type not in ("json", "form-urlencoded", "form-data"):
            self.template.init(data)
            render_value = self.template.render()
            self.template.request_body = render_value
        else:
            for expr, value in get_json_relation(data, name):
                if isinstance(value, str) and self.comp.search(value) is not None:
                    self.template.init(value)
                    render_value = self.template.render()
                    if name == "headers":
                        render_value = str(render_value)
                    expression = self.json_path_parser.parse(expr)
                    expression.update(data, render_value)
                    if name == "body":
                        self.template.request_body = data
                    elif name == "query":
                        self.template.request_query = data
                    else:
                        self.template.request_headers = data
        if name == "body":
            step.collector.others.setdefault(pop_key, self.template.request_body)
        elif name == "query":
            step.collector.others.setdefault("params", self.template.request_query)
        else:
            step.collector.others.setdefault("headers", self.template.request_headers)

