import os
from faker import Faker
from importlib import import_module, reload
import sys
from faker.providers import BaseProvider
from tools.funclib.params_enum import PARAMS_ENUM
from tools.funclib.provider.lm_provider import LiuMaProvider


class CustomFaker(Faker):
    def __init__(self, package='provider', test=None, lm_func=None, temp=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if lm_func is None:
            lm_func = []
        self.package = package
        self.test = test
        self.print = print
        self.lm_func = lm_func
        self.temp = temp
        self.func_param = PARAMS_ENUM
        self._load_module()
        self._load_lm_func()

    def __call__(self, name, *args, **kwargs):
        return getattr(self, name)(*args, **kwargs)

    def _load_module(self):
        self.add_provider(LiuMaProvider)    # 自定义函数库在此添加进来

    def _load_lm_func(self):
        for custom in self.lm_func:
            func = self._lm_custom_func(custom["name"], custom["code"], custom["params"]["names"], self.test, self.temp)
            params = []
            for value in custom["params"]["types"]:
                if value == "Int":
                    params.append(int)
                elif value == "Float":
                    params.append(float)
                elif value == "Boolean":
                    params.append(bool)
                elif value == "Bytes":
                    params.append(bytes)
                elif value == "JSONObject":
                    params.append(dict)
                elif value == "JSONArray":
                    params.append(list)
                elif value == "Other":
                    params.append(None)
                else:
                    params.append(str)
            self.func_param[custom["name"]] = params
            setattr(self, custom["name"], func)

    def _lm_custom_func(self, _function_name, _code, _params, _test, _temp):
        def func(*args):
            def print(*args, sep=' ', end='\n', file=None, flush=False):
                if file is None or file in (sys.stdout, sys.stderr):
                    file = names["_test_case"].stdout_buffer
                self.print(*args, sep=sep, end=end, file=file, flush=flush)

            def sys_return(res):
                names["_exec_result"] = res

            def sys_get(name):
                if name in names["_test_context"]:
                    return names["_test_context"][name]
                elif name in names["_test_params"]:
                    return names["_test_params"][name]
                else:
                    raise KeyError("不存在的公共参数或关联变量: {}".format(name))

            def sys_put(name, val, ps=False):
                if ps:
                    names["_test_case"].recordVariableTrack(name, val, "function-" + names["_function_name"],
                                                            names["_test_params"], "common")
                    names["_test_params"][name] = val
                else:
                    names["_test_case"].recordVariableTrack(name, val, "function-" + names["_function_name"],
                                                            names["_test_context"])
                    names["_test_context"][name] = val

            names = locals()
            names["_test_context"] = _temp["context"]
            names["_test_params"] = _temp["params"]
            names["_test_case"] = _test
            names["_function_name"] = _function_name
            for index, value in enumerate(_params):
                names[value] = args[index]
            exec(_code)
            return names["_exec_result"]
        return func
