import reflex as rx
from app.state import StockAgentState


def message_view(message: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.image(
                src=rx.cond(
                    message["role"] == "user",
                    f"https://api.dicebear.com/9.x/initials/svg?seed=User",
                    "/design_logo_application.png",
                ),
                class_name="h-8 w-8 rounded-full",
            ),
            rx.el.div(
                rx.el.div(
                    rx.markdown(
                        message["content"],
                        class_name="prose prose-sm max-w-none text-gray-800",
                    ),
                    class_name="bg-white p-4 rounded-lg shadow-sm border border-gray-100",
                ),
                class_name="w-full",
            ),
            class_name="flex items-start gap-4",
        ),
        class_name=rx.cond(
            message["role"] == "user", "p-4 rounded-lg", "p-4 rounded-lg"
        ),
    )


def tool_call_view(tool_call: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.icon("terminal", class_name="h-4 w-4 text-gray-500"),
            rx.el.span(
                f"Tool Call: {tool_call['name']}",
                class_name="font-mono text-xs font-semibold text-gray-700",
            ),
            rx.cond(
                tool_call["is_executing"],
                rx.spinner(class_name="h-4 w-4 text-violet-500"),
                rx.icon("square_check", class_name="h-4 w-4 text-green-500"),
            ),
            class_name="flex items-center gap-2",
        ),
        rx.el.div(
            rx.el.pre(rx.el.code(tool_call["args"].to_string(), class_name="text-xs")),
            class_name="mt-2 p-2 bg-gray-900 text-white rounded-md text-xs font-mono",
        ),
        rx.cond(
            tool_call["output"],
            rx.el.div(
                rx.el.div(
                    "Output:", class_name="text-xs font-semibold text-gray-600 mb-1"
                ),
                rx.el.pre(
                    rx.el.code(tool_call["output"], class_name="text-xs"),
                    class_name="p-2 bg-gray-100 border border-gray-200 rounded-md text-xs",
                ),
                class_name="mt-2",
            ),
            None,
        ),
        class_name="my-4 p-4 border border-gray-200 rounded-lg bg-gray-50/50",
    )


def example_queries() -> rx.Component:
    queries = [
        "What's the stock price for Tesla?",
        "Compare NVDA and AMD stock.",
        "Tell me about Microsoft (MSFT) stock.",
    ]
    return rx.el.div(
        rx.el.p("Try an example:", class_name="text-sm font-medium text-gray-500 mb-2"),
        rx.el.div(
            rx.foreach(
                queries,
                lambda q: rx.el.button(
                    q,
                    on_click=StockAgentState.set_query_from_example(q),
                    class_name="px-3 py-1 text-sm font-medium text-violet-700 bg-violet-100 rounded-full hover:bg-violet-200 transition-colors",
                ),
            ),
            class_name="flex flex-wrap gap-2",
        ),
        class_name="mt-6",
    )


def index() -> rx.Component:
    return rx.el.main(
        rx.el.div(
            rx.el.div(
                rx.el.div(
                    rx.image(
                        src="/design_logo_application.png", class_name="h-10 w-10"
                    ),
                    rx.el.h1(
                        "Stock Price Agent",
                        class_name="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-violet-600 to-purple-500",
                    ),
                    class_name="flex items-center justify-center gap-3 mb-8",
                ),
                rx.el.div(
                    rx.el.div(
                        rx.foreach(StockAgentState.conversation, message_view),
                        rx.cond(
                            StockAgentState.is_loading,
                            rx.el.div(
                                rx.foreach(
                                    StockAgentState.current_tool_calls, tool_call_view
                                ),
                                rx.cond(
                                    StockAgentState.conversation.length() > 0,
                                    rx.cond(
                                        StockAgentState.conversation[-1]["role"]
                                        == "assistant",
                                        message_view(StockAgentState.conversation[-1]),
                                        None,
                                    ),
                                    None,
                                ),
                                class_name="w-full",
                            ),
                            None,
                        ),
                        class_name="flex flex-col gap-4",
                    ),
                    class_name="flex-grow p-6 space-y-6 overflow-y-auto",
                ),
                rx.el.div(
                    rx.cond(
                        StockAgentState.conversation.length() == 0,
                        example_queries(),
                        None,
                    ),
                    rx.el.form(
                        rx.el.div(
                            rx.el.input(
                                placeholder="Ask about a stock, e.g., 'What is the price of GOOGL?'",
                                name="query",
                                class_name="w-full p-4 text-base font-medium bg-white border border-gray-200 rounded-xl shadow-sm focus:ring-2 focus:ring-violet-500 focus:border-transparent transition-all",
                                default_value=StockAgentState.query,
                                key=StockAgentState.query,
                            ),
                            rx.el.button(
                                rx.cond(
                                    StockAgentState.is_loading,
                                    rx.spinner(class_name="h-5 w-5"),
                                    rx.icon("arrow-up", class_name="h-5 w-5"),
                                ),
                                type="submit",
                                disabled=~StockAgentState.has_query
                                | StockAgentState.is_loading,
                                class_name="absolute right-2.5 top-1/2 -translate-y-1/2 p-2 bg-gradient-to-br from-violet-500 to-purple-600 text-white rounded-lg shadow-md hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none",
                            ),
                            class_name="relative w-full",
                        ),
                        on_submit=StockAgentState.process_query,
                        reset_on_submit=True,
                        width="100%",
                    ),
                    class_name="p-6 bg-white/50 backdrop-blur-sm border-t border-gray-200",
                ),
                class_name="flex flex-col h-[90vh] max-h-[700px] w-full max-w-3xl mx-auto bg-white rounded-2xl shadow-lg border border-gray-100 overflow-hidden",
            ),
            class_name="min-h-screen w-full flex items-center justify-center p-4 bg-gray-50",
        ),
        class_name="font-['Poppins']",
    )


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap",
            rel="stylesheet",
        ),
    ],
)
app.add_page(index, title="Stock Price Agent")