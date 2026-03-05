# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Development and debugging middleware for Agent Framework pipelines.

This module provides three middleware classes that plug into Agent Framework’s
middleware chain at different interception points:

Middleware types (from outermost to innermost):
    ``AgentMiddleware``  → wraps the entire ``agent.run()`` / ``agent.run_stream()``
    ``ChatMiddleware``   → wraps the chat-client call (messages in / response out)
    ``FunctionMiddleware`` → wraps individual tool / function invocations

Classes:
    DebuggingMiddleware
        ``AgentMiddleware`` that prints run-level diagnostics (message count,
        streaming flag, metadata) before and after the agent executes.
    LoggingFunctionMiddleware
        ``FunctionMiddleware`` that logs every tool call with argument details,
        execution duration, and truncated output.
    InputObserverMiddleware
        ``ChatMiddleware`` that logs and optionally replaces the text of user
        messages before they reach the LLM.

Note:
    These middlewares use ``print()`` for output and are intended for local
    development / debugging only.  For production observability, prefer
    structured logging via ``logging.getLogger``.
"""

import time
from collections.abc import Awaitable, Callable

from agent_framework import (
    AgentMiddleware,
    AgentRunContext,
    ChatContext,
    ChatMessage,
    ChatMiddleware,
    FunctionInvocationContext,
    FunctionMiddleware,
    Role,
)


class DebuggingMiddleware(AgentMiddleware):
    """Run-level debugging middleware that prints diagnostic info.

    Intercepts the ``AgentRunContext`` before the agent executes and prints:
        - Total message count in the context.
        - Whether the run is streaming.
        - Any pre-existing metadata.

    After execution it prints a completion marker.  The middleware also injects
    ``debug_enabled=True`` into ``context.metadata`` so downstream code can
    detect that debugging is active.
    """

    async def process(
        self,
        context: AgentRunContext,
        next: Callable[[AgentRunContext], Awaitable[None]],
    ) -> None:
        """Print run diagnostics, inject debug flag, and delegate to next.

        Processing steps:
            1. Print message count, streaming flag, and existing metadata.
            2. Set ``context.metadata['debug_enabled'] = True``.
            3. Await ``next(context)`` to run the rest of the pipeline.
            4. Print a completion marker.

        Args:
            context: The run context containing messages, metadata, and
                streaming configuration.
            next: Callable that invokes the next middleware or the agent itself.
        """
        print("[Debug] Debug mode enabled for this run")
        print(f"[Debug] Messages count: {len(context.messages)}")
        print(f"[Debug] Is streaming: {context.is_streaming}")

        # Log existing metadata from agent middleware
        if context.metadata:
            print(f"[Debug] Existing metadata: {context.metadata}")

        context.metadata["debug_enabled"] = True

        await next(context)

        print("[Debug] Debug information collected")


class LoggingFunctionMiddleware(FunctionMiddleware):
    """Function-call logging middleware with execution timing.

    Wraps every tool / function invocation and prints a formatted report
    containing:
        - Function name and arguments.
        - Wall-clock execution duration.
        - Output results (truncated to 1 000 characters for large payloads).
        - Error flag if the result reports ``is_error``.

    This is useful during development to trace exactly which tools the agent
    calls and what data flows through them.
    """

    async def process(
        self,
        context: FunctionInvocationContext,
        next: Callable[[FunctionInvocationContext], Awaitable[None]],
    ) -> None:
        """Log a tool invocation with timing, arguments, and results.

        Processing steps:
            1. Capture function name and argument details from the context.
            2. Record ``start_time``, then await ``next(context)``.
            3. Compute elapsed duration.
            4. Print a bordered report with function name, duration,
               arguments, and output (truncated if > 1 000 chars).

        Args:
            context: The function invocation context providing the function
                metadata, arguments, and (after execution) the result.
            next: Callable that invokes the next middleware or the function.
        """
        function_name = context.function.name

        # Collect arguments for display
        args_info = []
        if context.arguments:
            for key, value in context.arguments.model_dump().items():
                args_info.append(f"{key}: {value}")

        start_time = time.time()
        await next(context)
        end_time = time.time()
        duration = end_time - start_time

        # Build comprehensive log output
        print("\n" + "=" * 80)
        print("[LoggingFunctionMiddleware] Function Call")
        print("=" * 80)
        print(f"Function Name: {function_name}")
        print(f"Execution Time: {duration:.5f}s")

        # Display arguments
        if args_info:
            print("\nArguments:")
            for arg in args_info:
                print(f"  - {arg}")
        else:
            print("\nArguments: None")

        # Display output results
        if context.result:
            print("\nOutput Results:")

            # Ensure context.result is treated as a list
            results = (
                context.result if isinstance(context.result, list) else [context.result]
            )

            for idx, result in enumerate(results):
                print(f"  Result #{idx + 1}:")

                # Use raw_representation to get the actual output
                if hasattr(result, "raw_representation"):
                    raw_output = result.raw_representation
                    raw_type = type(raw_output).__name__
                    print(f"    Type: {raw_type}")

                    # Limit output length for very large content
                    output_str = str(raw_output)
                    if len(output_str) > 1000:
                        print(f"    Output (truncated): {output_str[:1000]}...")
                    else:
                        print(f"    Output: {output_str}")
                # result is just string or primitive
                else:
                    output_str = str(result)
                    if len(output_str) > 1000:
                        print(f"    Output (truncated): {output_str[:1000]}...")
                    else:
                        print(f"    Output: {output_str}")

                # Check if result has error flag
                if hasattr(result, "is_error"):
                    print(f"    Is Error: {result.is_error}")
        else:
            print("\nOutput Results: None")

        print("=" * 80 + "\n")


class InputObserverMiddleware(ChatMiddleware):
    """Chat middleware that observes and optionally rewrites user messages.

    When injected into an agent’s middleware stack, this class:
        1. Prints every message in the chat context (role + content).
        2. If ``replacement`` is set, replaces the text of all ``USER`` messages
           with the configured string.
        3. Prints a completion marker after the pipeline finishes.

    This is primarily a development tool for testing how an agent responds to
    fixed inputs regardless of what the caller actually sent.
    """

    def __init__(self, replacement: str | None = None) -> None:
        """Configure the observer with an optional message replacement.

        Args:
            replacement: If provided, every ``USER`` message’s text will be
                replaced with this string before the LLM sees it.  If ``None``,
                messages are logged but not modified.
        """
        self.replacement = replacement

    async def process(
        self,
        context: ChatContext,
        next: Callable[[ChatContext], Awaitable[None]],
    ) -> None:
        """Log input messages, optionally rewrite user text, then delegate.

        Processing steps:
            1. Print each message’s role and content.
            2. Print total message count.
            3. Walk all messages; for ``USER`` messages with text, replace the
               text with ``self.replacement`` if set.
            4. Replace ``context.messages`` with the (possibly modified) list.
            5. Await ``next(context)`` to proceed to the LLM call.
            6. Print a completion marker.

        Args:
            context: The chat context containing the message list.
            next: Callable that invokes the next middleware or the chat client.
        """
        print("[InputObserverMiddleware] Observing input messages:")

        for i, message in enumerate(context.messages):
            content = message.text if message.text else str(message.contents)
            print(f"  Message {i + 1} ({message.role.value}): {content}")

        print(f"[InputObserverMiddleware] Total messages: {len(context.messages)}")

        # Modify user messages by creating new messages with enhanced text
        modified_messages: list[ChatMessage] = []
        modified_count = 0

        for message in context.messages:
            if message.role == Role.USER and message.text:
                original_text = message.text
                updated_text = original_text

                if self.replacement:
                    updated_text = self.replacement
                    print(
                        f"[InputObserverMiddleware] Updated: '{original_text}' -> '{updated_text}'"
                    )

                modified_message = ChatMessage(role=message.role, text=updated_text)
                modified_messages.append(modified_message)
                modified_count += 1
            else:
                modified_messages.append(message)

        # Replace messages in context
        context.messages[:] = modified_messages

        # Continue to next middleware or AI execution
        await next(context)

        # Observe that processing is complete
        print("[InputObserverMiddleware] Processing completed")
