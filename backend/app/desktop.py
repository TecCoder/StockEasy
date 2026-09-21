"""Run StockEasy as a launcher-owned local server."""

import uvicorn

from app.main import create_app


def main() -> None:
    app = create_app()
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=8000,
        access_log=False,
    )
    server = uvicorn.Server(config)

    def request_shutdown() -> None:
        server.should_exit = True

    app.state.shutdown_callback = request_shutdown
    server.run()


if __name__ == "__main__":
    main()
