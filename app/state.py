import reflex as rx
from typing import TypedDict, Any
import asyncio
import json
import logging
import yfinance as yf
from agno.agent import Agent, RunOutputEvent, RunEvent
from agno.models.google import Gemini
import os


class Message(TypedDict):
    role: str
    content: str
    tool_calls: list[dict] | None
    tool_outputs: list[dict] | None


class ToolCall(TypedDict):
    name: str
    args: dict
    output: str | None
    is_executing: bool


def get_stock_price(symbol: str) -> str:
    """Get the current stock price and key information for a given ticker symbol.

    Args:
        symbol (str): The stock ticker symbol (e.g., 'AAPL', 'GOOGL', 'TSLA')

    Returns:
        str: JSON string with stock information
    """
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        hist = stock.history(period="1d")
        if hist.empty or "currentPrice" not in info:
            return json.dumps(
                {
                    "error": f"No data found for symbol {symbol}. It might be an invalid ticker."
                }
            )
        current_price = info.get("currentPrice")
        result = {
            "symbol": symbol.upper(),
            "current_price": round(float(current_price), 2),
            "currency": info.get("currency", "USD"),
            "company_name": info.get("shortName", symbol),
            "market_cap": info.get("marketCap"),
            "day_high": round(float(hist["High"].iloc[-1]), 2)
            if "High" in hist and (not hist["High"].empty)
            else None,
            "day_low": round(float(hist["Low"].iloc[-1]), 2)
            if "Low" in hist and (not hist["Low"].empty)
            else None,
        }
        return json.dumps(result)
    except Exception as e:
        logging.exception(f"Error getting stock price for {symbol}: {e}")
        return json.dumps({"error": str(e)})


class StockAgentState(rx.State):
    query: str = ""
    is_loading: bool = False
    conversation: list[Message] = []
    current_tool_calls: list[ToolCall] = []

    @rx.var
    def has_query(self) -> bool:
        return bool(self.query.strip())

    def _set_query(self, value: str):
        self.query = value

    @rx.event
    def set_query_from_example(self, example_query: str):
        self.query = example_query
        return StockAgentState.process_query

    @rx.event(background=True)
    async def process_query(self, form_data: dict[str, str] | None = None):
        if form_data:
            query = form_data.get("query", "").strip()
        else:
            async with self:
                query = self.query.strip()
        if not query:
            return
        async with self:
            user_message: Message = {
                "role": "user",
                "content": query,
                "tool_calls": None,
                "tool_outputs": None,
            }
            self.conversation.append(user_message)
            self.is_loading = True
            self.query = ""
            self.current_tool_calls = []
        try:
            agent = Agent(
                model=Gemini(id="gemini-2.0-flash-exp"),
                tools=[get_stock_price],
                instructions="You are a helpful stock market assistant. When asked about stock prices, use the get_stock_price tool to fetch real-time data. Be concise and friendly. Format stock data clearly.",
                markdown=True,
            )
            stream: RunOutputEvent = agent.run(user_message["content"], stream=True)
            assistant_message: Message = {
                "role": "assistant",
                "content": "",
                "tool_calls": [],
                "tool_outputs": [],
            }
            async with self:
                self.conversation.append(assistant_message)
                yield
            for chunk in stream:
                async with self:
                    if (
                        chunk.event == RunEvent.run_content
                        and hasattr(chunk, "content")
                        and chunk.content
                    ):
                        self.conversation[-1]["content"] += chunk.content
                    elif (
                        chunk.event == RunEvent.tool_call_started
                        and hasattr(chunk, "tool")
                        and chunk.tool
                    ):
                        tool_call_data: ToolCall = {
                            "name": chunk.tool.tool_name,
                            "args": chunk.tool.tool_args,
                            "output": None,
                            "is_executing": True,
                        }
                        self.current_tool_calls.append(tool_call_data)
                    elif (
                        chunk.event == RunEvent.tool_call_completed
                        and hasattr(chunk, "tool")
                        and chunk.tool
                    ):
                        for i, call in enumerate(self.current_tool_calls):
                            if call["name"] == chunk.tool.tool_name:
                                self.current_tool_calls[i]["output"] = chunk.tool.result
                                self.current_tool_calls[i]["is_executing"] = False
                                break
                yield
        except Exception as e:
            logging.exception(f"Error processing query: {e}")
            error_message = f"An error occurred: {str(e)}"
            async with self:
                if self.conversation and self.conversation[-1]["role"] == "assistant":
                    self.conversation[-1]["content"] = error_message
                else:
                    self.conversation.append(
                        {
                            "role": "assistant",
                            "content": error_message,
                            "tool_calls": [],
                            "tool_outputs": [],
                        }
                    )
        finally:
            async with self:
                self.is_loading = False