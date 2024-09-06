from ws4py.client.threadedclient import WebSocketClient


class WSClient(WebSocketClient):

    def __init__(self, test, current_index, url, msg_queue=None, ssl_options=None, headers=None):
        self.test = test
        self.url = url
        self.current_index = current_index
        self.msg_queue = msg_queue
        WebSocketClient.__init__(self, url, ssl_options=ssl_options, headers=headers)

    def opened(self):
        self.test.debugLog("websocket接口建立链接，链接信息：%s" % self.url, self.current_index)

    def closed(self, code, reason=None):
        self.test.debugLog("websocket链接已关闭", self.current_index)

    def unhandled_error(self, error):
        self.test.errorLog("websocket链接发生错误，错误信息：%s" % str(error), self.current_index)

    def received_message(self, resp):
        if resp.is_text:
            message = str(resp)
        else:
            message = resp.data
        if self.msg_queue is not None:
            self.msg_queue.append(message)

