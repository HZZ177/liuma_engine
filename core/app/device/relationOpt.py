import sys

from uiautomator2 import UiObjectNotFoundError
from core.app.device import Operation


class Relation(Operation):
    """关联类操作"""
    def get_window_size(self, system, save_name):
        """提取屏幕尺寸"""
        try:
            if system == "android":
                w, h = self.device.window_size()
                actual = (w, h)
            else:
                size = self.device.window_size()
                actual = (size.width, size.height)
            self.test.debugLog("成功获取屏幕尺寸:%s" % str(actual))
        except Exception as e:
            self.test.errorLog("无法获取屏幕尺寸")
            raise e
        else:
            self.test.recordVariableTrack(save_name, actual, "relation", self.test.context)
            self.test.context[save_name] = actual

    def get_window_width(self, system, save_name):
        """提取屏幕宽度"""
        try:
            if system == "android":
                w, h = self.device.window_size()
                actual = w
            else:
                size = self.device.window_size()
                actual = size.width
            self.test.debugLog("成功获取屏幕宽度:%s" % str(actual))
        except Exception as e:
            self.test.errorLog("无法获取屏幕宽度")
            raise e
        else:
            self.test.recordVariableTrack(save_name, actual, "relation", self.test.context)
            self.test.context[save_name] = actual

    def get_window_height(self, system, save_name):
        """提取屏幕高度"""
        try:
            if system == "android":
                w, h = self.device.window_size()
                actual = h
            else:
                size = self.device.window_size()
                actual = size.height
            self.test.debugLog("成功获取屏幕高度:%s" % str(actual))
        except Exception as e:
            self.test.errorLog("无法获取屏幕高度")
            raise e
        else:
            self.test.recordVariableTrack(save_name, actual, "relation", self.test.context)
            self.test.context[save_name] = actual

    def get_ele_text(self, system, element, save_name):
        """提取元素文本"""
        try:
            if system == "android":
                actual = self.find_element(element).get_text()
            else:
                actual = self.find_element(element).text
            self.test.debugLog("成功获取元素文本:%s" % str(actual))
        except Exception as e:
            self.test.errorLog("无法获取元素文本")
            raise e
        else:
            self.test.recordVariableTrack(save_name, actual, "relation", self.test.context)
            self.test.context[save_name] = actual

    def get_ele_center(self, system, element, save_name):
        """提取元素位置"""
        try:
            if system == "android":
                x, y = self.find_element(element).center()
                actual = (x, y)
            else:
                x, y = self.find_element(element).bounds.center
                actual = (x, y)
            self.test.debugLog("成功获取元素位置:%s" % str(actual))
        except Exception as e:
            self.test.errorLog("无法获取元素位置")
            raise e
        else:
            self.test.recordVariableTrack(save_name, actual, "relation", self.test.context)
            self.test.context[save_name] = actual

    def get_ele_x(self, system, element, save_name):
        """提取元素X坐标"""
        try:
            if system == "android":
                x, y = self.find_element(element).center()
                actual = x
            else:
                x, y = self.find_element(element).bounds.center
                actual = x
            self.test.debugLog("成功获取元素X坐标:%s" % str(actual))
        except Exception as e:
            self.test.errorLog("无法获取元素X坐标")
            raise e
        else:
            self.test.recordVariableTrack(save_name, actual, "relation", self.test.context)
            self.test.context[save_name] = actual

    def get_ele_y(self, system, element, save_name):
        """提取元素Y坐标"""
        try:
            if system == "android":
                x, y = self.find_element(element).center()
                actual = y
            else:
                x, y = self.find_element(element).bounds.center
                actual = y
            self.test.debugLog("成功获取元素Y坐标:%s" % str(actual))
        except Exception as e:
            self.test.errorLog("无法获取元素Y坐标")
            raise e
        else:
            self.test.recordVariableTrack(save_name, actual, "relation", self.test.context)
            self.test.context[save_name] = actual

    def get_alert_text(self, save_name):
        """提取弹框文本 IOS专属"""
        try:
            actual = self.device.alert.text
            self.test.debugLog("成功获取弹框文本:%s" % str(actual))
        except Exception as e:
            self.test.errorLog("无法获取弹框文本")
            raise e
        else:
            self.test.recordVariableTrack(save_name, actual, "relation", self.test.context)
            self.test.context[save_name] = actual

    def custom(self, **kwargs):
        """自定义"""
        code = kwargs["code"]
        names = locals()
        names["element"] = kwargs["element"]
        names["data"] = kwargs["data"]
        names["device"] = self.device
        names["test"] = self.test
        names["_test_case"] = self.test
        try:
            """关联操作需要返回被关联的值 以sys_return(value)返回"""
            def print(*args, sep=' ', end='\n', file=None, flush=False):
                if file is None or file in (sys.stdout, sys.stderr):
                    file = names["_test_case"].stdout_buffer
                self.print(*args, sep=sep, end=end, file=file, flush=flush)

            def sys_return(res):
                names["_exec_result"] = res

            def sys_get(name):
                if name in names["_test_case"].context:
                    return names["_test_case"].context[name]
                elif name in names["_test_case"].common_params:
                    return names["_test_case"].common_params[name]
                else:
                    raise KeyError("不存在的公共参数或关联变量: {}".format(name))

            def sys_put(name, val, ps=False):
                if ps:
                    names["_test_case"].recordVariableTrack(name, val, "operation", names["_test_case"].common_params, "common")
                    names["_test_case"].common_params[name] = val
                else:
                    names["_test_case"].recordVariableTrack(name, val, "operation", names["_test_case"].context)
                    names["_test_case"].context[name] = val

            exec(code)
            self.test.debugLog("成功执行 %s" % kwargs["trans"])
        except UiObjectNotFoundError as e:
            raise e
        except Exception as e:
            self.test.errorLog("无法执行 %s" % kwargs["trans"])
            raise e
        else:
            self.test.recordVariableTrack(kwargs["data"]["save_name"], names["_exec_result"], "relation",
                                          self.test.context)
            self.test.context[kwargs["data"]["save_name"]] = names["_exec_result"]

