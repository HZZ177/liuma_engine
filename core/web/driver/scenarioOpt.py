import sys

from selenium.common.exceptions import NoSuchElementException
from core.web.driver import Operation


class Scenario(Operation):
    """场景类类操作"""

    def custom(self, **kwargs):
        """自定义"""
        code = kwargs["code"]
        names = locals()
        names["element"] = kwargs["element"]
        names["data"] = kwargs["data"]
        names["driver"] = self.driver
        names["test"] = self.test
        names["_test_case"] = self.test
        try:
            def print(*args, sep=' ', end='\n', file=None, flush=False):
                if file is None or file in (sys.stdout, sys.stderr):
                    file = names["_test_case"].stdout_buffer
                self.print(*args, sep=sep, end=end, file=file, flush=flush)

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
        except NoSuchElementException as e:
            raise e
        except Exception as e:
            self.test.errorLog("无法执行 %s" % kwargs["trans"])
            raise e
