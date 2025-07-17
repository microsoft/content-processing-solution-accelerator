import logging
from multiprocessing import Process
from typing import Any, Tuple

from pydantic import BaseModel

from libs.application.application_context import AppContext


class HandlerInfo(BaseModel):
    handler: Process = None
    target_function: object = None
    args: Tuple[Any, AppContext, str] = None

    class Config:
        arbitrary_types_allowed = True


class HandlerHostManager:
    handlers: list[dict[str, HandlerInfo]] = []

    def __init__(self, **data):
        super().__init__(**data)
        self.handlers = []

    def add_handlers_as_process(
        self,
        target_function: object,
        process_name: str,
        args: Tuple[Any, AppContext, str],
    ):
        handler_process = Process(target=target_function, name=process_name, args=args)

        self.handlers.append(
            {
                "handler_name": process_name,
                "handler_info": HandlerInfo(
                    handler=handler_process, target_function=target_function, args=args
                ),
            }
        )

    async def start_handler_processes(self, test_mode: bool = False):
        for handler in self.handlers:
            handler["handler_info"].handler.start()

        while not test_mode:
            for handler in self.handlers:
                handler["handler_info"].handler.join(timeout=1)
                if (
                    not handler["handler_info"].handler.is_alive()
                    or handler["handler_info"].handler.exitcode is not None
                ):
                    print(f"Restarting the handler => {handler['handler_name']}")
                    # Remove Process from the list by name
                    self.handlers.remove(handler)
                    # Log the error
                    print(
                        f"Handler {handler['handler_name']} has stopped with exit code {handler['handler_info'].handler.exitcode}"
                    )
                    # restart the process
                    new_handler = self._restart_handler(
                        handler["handler_name"],
                        handler["handler_info"].target_function,
                        handler["handler_info"].args,
                    )
                    self.handlers.append(
                        {
                            "handler_name": handler["handler_name"],
                            "handler_info": HandlerInfo(
                                handler=new_handler,
                                target_function=handler["handler_info"].target_function,
                                args=handler["handler_info"].args,
                            ),
                        }
                    )

            # await asyncio.sleep(3)

    def _restart_handler(self, handler_name, target_function, args):
        new_handler = Process(target=target_function, name=handler_name, args=args)
        new_handler.start()
        logging.info(f"Handler process {new_handler.name} has been restarted")
        return new_handler
