import reflex as rx

config = rx.Config(
    app_name="developer_console",
    frontend_port=3001,
    backend_port=8001,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(),
    ]
)