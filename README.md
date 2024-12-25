# Alpaca Market Data Fetcher

Handler for making a ton of asynchronous API requests to [Alpaca Markets](https://alpaca.markets/)

# Installation

```
git clone data_fetcher
```

# Prerequisites

### `uv` System

This repo runs on [`uv`, the extremely fast package manager for Python written in Rust](https://docs.astral.sh/uv/), which you will need to use. It has very thorough documentation for getting set up. We outline the minimal steps to get set up here:

1. You will need to install it. [It's very easy](https://docs.astral.sh/uv/getting-started/installation/).
2. Run `uv venv` to build a virtualenv managed in Rust (so much faster)
3. Run `uv sync` to make the `uv.lock` file, which holds all dependencies, write the dependencies to the environment.
4. Run `uv run main.py` to run the `main.py` in place of `python3 main.py`.

# Installation

### Authentication and `config.ini`

##### Authentication

We have 2 parameters that we use. You will need to retrieve the values from your Alpaca Account. [Please follow this documentation to do so.](https://alpaca.markets/learn/connect-to-alpaca-api)

###### Example `config.ini`

Must keep the `DEFAULT` section.

```
[DEFAULT]
API-KEY = <Alpaca API Key>
API-SECRET = <Alpaca Secret>
```

# Examples

### UI Request

To learn more about the Alpaca Market API, you can [use this link](https://docs.alpaca.markets/reference/stocktrades-1) to practice pulling the data.

### Using `data_fetcher`

It's a shoddy package-like implementation. `main.py` has an example. The [API docs tell you the values](https://docs.alpaca.markets/reference/stockbars) to pass to the API.

##### Anecdotal runtime

| History | Interval        | Runtime       |
| ------- | --------------- | ------------- |
| 2 Years | 3Month interval | ~5 minutes    |
| 5 Years | 5Min interval   | over an hours |
