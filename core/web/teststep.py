import sys
from datetime import datetime
from core.assertion import LMAssert
from core.web.find_opt import *


class WebTestStep:
    def __init__(self, test, driver, context, collector):
        self.test = test
        self.driver = driver
        self.context = context
        self.collector = collector
        self.result = None

    def execute(self):
        try:
            self.test.debugLog('WEB操作[{}]开始'.format(self.collector.opt_name))
            opt_type = self.collector.opt_type
            if opt_type == "browser":
                func = find_browser_opt(self.collector.opt_name)
            elif opt_type == "page":
                func = find_page_opt(self.collector.opt_name)
            elif opt_type == "condition":
                func = find_condition_opt(self.collector.opt_name)
            elif opt_type == "assertion":
                func = find_assertion_opt(self.collector.opt_name)
            elif opt_type == "relation":
                func = find_relation_opt(self.collector.opt_name)
            else:
                func = find_scenario_opt(self.collector.opt_name)
            if func is None:
                raise NotExistedWebOperation("未定义操作")
            opt_content = {
                "trans": self.collector.opt_trans,
                "code": self.collector.opt_code,
                "element": self.collector.opt_element,
                "data": self.collector.opt_data
            }
            self.result = func(self.test, self.driver, **opt_content)
            self.log_show()
        finally:
            self.test.debugLog('WEB操作[{}]结束'.format(self.collector.opt_name))

    def looper_controller(self, case, opt_list, step_n, current_index):
        """循环控制器"""
        self.test.debugLog('WEB操作[{}]开始'.format(self.collector.opt_name))
        if self.collector.opt_trans == "While循环":
            loop_start_time = datetime.now()
            timeout = int(self.collector.opt_data["timeout"]["value"])
            index = 0
            self.test.recordTransDetail("type", "while")
            while timeout == 0 or (datetime.now() - loop_start_time).seconds * 1000 < timeout:
                # timeout为0时可能会死循环 慎重选择
                index_name = self.collector.opt_data["indexName"]["value"]
                self.test.recordVariableTrack(index_name, index, "looper", self.context, index=current_index)
                self.context[index_name] = index  # 给循环索引赋值第几次循环 母循环和子循环的索引名不应一样
                _looper = case.render_looper(self.collector.opt_data)  # 渲染循环控制控制器 每次循环都需要渲染
                index += 1
                result, msg = LMAssert(_looper['assertion'], _looper['target'], _looper['expect']).compare()
                if not result:
                    self.test.debugLog('[循环控制器]第{}次循环时不满足循环条件, 结束循环, 当前判断结果:{}'.format(index, msg), current_index)
                    break
                else:
                    self.test.debugLog('[循环控制器]第{}次循环时满足循环条件, 继续循环, 当前判断结果:{}'.format(index, msg), current_index)
                _opt_list = opt_list[step_n+1: (step_n + _looper["steps"]+1)]   # 循环操作本身不参与循环 不然死循环
                case.loop_execute(_opt_list, [], parent_index=current_index)
            else:
                self.test.debugLog('[循环控制器]当前循环超时, 结束循环', current_index)
        else:
            self.test.recordTransDetail("type", "for")
            _looper = case.render_looper(self.collector.opt_data)    # 渲染循环控制控制器 for只需渲染一次
            self.test.debugLog('[循环控制器]for循环执行开始, 循环次数:{}, 循环索引名:{}'.format(_looper["times"], _looper["indexName"]))
            for index in range(_looper["times"]):  # 本次循环次数
                self.test.recordVariableTrack(_looper["indexName"], index, "looper", self.context, index=current_index)
                self.context[_looper["indexName"]] = index  # 给循环索引赋值第几次循环 母循环和子循环的索引名不应一样
                _opt_list = opt_list[step_n+1: (step_n + _looper["steps"]+1)]
                case.loop_execute(_opt_list, [], parent_index=current_index)
            else:
                self.test.debugLog('[循环控制器]当前循环完成, 结束循环', current_index)
        self.test.debugLog('WEB操作[{}]结束'.format(self.collector.opt_name), current_index)
        return int(self.collector.opt_data["steps"]["value"])

    def condition_controller(self, case, opt_list, step_n, current_index):
        offset_true = self.collector.opt_data["true"]
        if not isinstance(offset_true, int):
            offset_true = 0
        offset_false = self.collector.opt_data["false"]
        if not isinstance(offset_false, int):
            offset_false = 0
        if self.result[0]:
            self.test.recordTransDetail("result", True)
            self.test.debugLog('[条件控制器]条件判断为真, 执行True分支, 条件信息: {}'.format(self.result[1]), current_index)
            skip_steps = [i for i in range(offset_true, offset_true + offset_false)]
        else:
            self.test.recordTransDetail("result", False)
            self.test.debugLog('[条件控制器]条件判断为假, 执行False分支, 条件信息: {}'.format(self.result[1]), current_index)
            skip_steps = [i for i in range(0, offset_true)]
        _opt_list = opt_list[step_n + 1: (step_n + offset_true + offset_false + 1)]
        case.loop_execute(_opt_list, skip_steps, parent_index=current_index)
        return offset_true + offset_false

    def assert_controller(self):
        if self.result[0]:
            self.test.debugLog('[{}]断言成功: {}'.format(self.collector.opt_trans,
                                                         self.result[1]))
        else:
            self.test.errorLog('[{}]断言失败: {}'.format(self.collector.opt_trans,
                                                         self.result[1]))
            self.test.saveScreenShot(self.collector.opt_trans, self.driver.get_screenshot_as_png())
            if "continue" in self.collector.opt_data and self.collector.opt_data["continue"] is True:
                try:
                    raise AssertionError(self.result[1])
                except AssertionError:
                    error_info = sys.exc_info()
                    self.test.recordFailStatus(error_info)
            else:
                raise AssertionError(self.result[1])

    def log_show(self):
        msg = ""
        if self.collector.opt_element is not None:
            for k, v in self.collector.opt_element.items():
                msg += '元素定位: {}: {}<br>'.format(k, v)
        if self.collector.opt_data is not None:
            data_log = '{'
            for k, v in self.collector.opt_data.items():
                data_log += "{}: {}, ".format(k, v)
            if len(data_log) > 1:
                data_log = data_log[:-2]
            data_log += '}'
            msg += '操作数据: {}'.format(data_log)
        if msg != "":
            msg = '操作信息: <br>' + msg
            self.test.debugLog(msg)


class NotExistedWebOperation(Exception):
    """未定义的WEB操作"""
