import reflex as rx

config = rx.Config(
    app_name="ai_hybrid_evaluator",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
    ]
)