from collections.abc import Callable


class EventBus:
    def __init__(self):
        self.subscribers: dict[str, list[Callable]] = {}

    def subscribe(self, topic: str, callback: Callable):
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        self.subscribers[topic].append(callback)

    def emit(self, topic: str, data: dict):
        if topic in self.subscribers:
            for callback in self.subscribers[topic]:
                callback(data)
        # Also emit to a global 'all' topic
        for callback in self.subscribers.get("all", []):
            callback({"topic": topic, "data": data})
