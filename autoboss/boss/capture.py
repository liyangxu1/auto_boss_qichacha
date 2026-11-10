"""监听浏览器自然产生的详情响应，不独立请求 BOSS 私有接口。"""

from urllib.parse import urlsplit

from .extract import is_detail_response, parse_detail_response


class DetailCapture:
    def __init__(self, context):
        self.context = context
        self.responses = []
        self.parsed = {}

    def receive(self, response):
        if is_detail_response(response):
            self.responses.append(response)

    def __enter__(self):
        self.context.on("response", self.receive)
        return self

    def __exit__(self, *args):
        self.context.remove_listener("response", self.receive)

    def find(self, card, since=0):
        matches = {}
        for response in self.responses[since:]:
            if response not in self.parsed:
                try:
                    self.parsed[response] = parse_detail_response(response.json())
                except Exception:
                    continue
            detail = self.parsed[response]
            if not detail or not self.matches(card, detail):
                continue
            matches[detail.get("url") or detail["title"]] = detail
        # 无岗位链接时，重名岗位不能靠名称随意绑定。
        return next(iter(matches.values())) if len(matches) == 1 else None

    @staticmethod
    def matches(card, detail):
        if card.get("url") and detail.get("url"):
            return urlsplit(card["url"]).path == urlsplit(detail["url"]).path
        if card["title"].strip() != detail["title"].strip():
            return False
        return not (card.get("company_name") and detail.get("company_name")
                    and card["company_name"].strip() != detail["company_name"].strip())
