# -*- coding: utf-8 -*-
import datetime, time
import os
import shutil
from lm.lm_api import LMApi
from lm.lm_log import DebugLogger, ErrorLogger
from lm.lm_config import DATA_PATH


class LMReport(object):
    def __init__(self, message_queue, case_result_queue):
        self.case_result_queue = case_result_queue
        self.message_queue = message_queue
        self.api = LMApi()

    def monitor_result(self):
        not_send_result = []
        last_send_time = datetime.datetime.now()
        while True:
            try:
                message = self.case_result_queue.get()
            except Exception as e:
                DebugLogger("获取执行结果报错 错误信息%s" % str(e))
            else:
                if isinstance(message, str):
                    if "run_all_start" in message:
                        task_id = message.split("--")[1]
                        data_type = message.split("--")[-1]
                        DebugLogger("任务执行启动 开始监听执行结果 任务id: %s" % task_id)
                    elif "run_all_stop" in message:
                        if len(not_send_result) != 0:
                            self.api.upload_result(task_id, data_type, not_send_result)
                        self.post_stop(task_id)  # 执行结束
                        self.message_queue.put({"type": "completed", "data": task_id})  # 通知任务管理器清空当前执行任务
                        time.sleep(2)
                        break
                    else:   # start_run_index--n
                        if len(not_send_result) != 0:
                            self.api.upload_result(task_id, data_type, not_send_result)
                            not_send_result.clear()
                        index = int(message.split("--")[-1])
                        if index > 0:
                            DebugLogger("用例有执行错误 重试执行 任务id: %s" % task_id)
                else:
                    """控制请求频率"""
                    result = message
                    not_send_result.append(result)
                    current_time = datetime.datetime.now()
                    during = (current_time - last_send_time).seconds
                    if during < 3:
                        pass
                    else:
                        self.api.upload_result(task_id, data_type, not_send_result)
                        last_send_time = current_time
                        not_send_result.clear()

    def post_stop(self, task_id=None):
        DebugLogger("任务执行结束 调用接口通知平台 任务id: %s" % task_id)
        self.api.complete_task(task_id)
        data = os.path.join(DATA_PATH, str(task_id))
        if os.path.exists(data):
            try:
                shutil.rmtree(data)
            except Exception as e:
                ErrorLogger("删除测试数据失败 失败原因：%s 任务id: %s" % (str(e), task_id))
