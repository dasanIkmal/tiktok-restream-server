import requests as req
from logger_manager import LoggerManager


class HttpClient:

    def __init__(self, logger: LoggerManager):
        self.req = None
        self.logger = logger
        self.configure_session()

    def configure_session(self) -> None:
        self.req = req.Session()
        self.req.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/"
        })

    def close_session(self):
        if self.req:
            self.req.close()
            self.logger.info("HTTP session closed")


