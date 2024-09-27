![Emerald Fund Logo](resources/EmeraldFundLogo.png)

# "There's magic in giving"

The official Emerald Fund Dashboard plugin is a result of years of Hummingbot usage. With it's own Strategy format, you can create, backtest, and optimize in 1 place, without ever having to leave the Hummingbot Dashboard!

The goal is to be user-friendly while offering all the features that Hummingbot V2 has, in a beginner-friendly package.

# Tutorial + Demo

Here's everything you need to know: https://youtu.be/5jaC5fbqK6M

# Features

- Easy to install on top of the official Hummingbot Deploy
- Completely made up-to-date with V2 strategies, backend API and the Dashboard
- Custom V2 strategy format: Create, backtest, optimize in 1 place
- Automatic support for Optuna optimization (no need to code this yourself)
- Multi strategy: Both directional and perpetual market making is supported!
- Extremely powerful Optuna optimizer framework: Test your strategies against multiple market conditions, improved performance and better overview of your strategy's strong and weak spots.

# How to install

- Follow the official Hummingbot deploy tutorial at https://github.com/hummingbot/deploy
- Once done, merge the `add_to_deploy` folder in this repo with the deploy folder you created in the first step
- Add `- ./bots:/backend-api/bots` to `deploy/docker-compose.yml` under dashboard `volumes:`

  <details>
    <summary>Full example</summary>

    ```yml   
    services:
      dashboard:
        container_name: dashboard
        image: hummingbot/dashboard:latest
        ports:
          - "8501:8501"
        environment:
            - AUTH_SYSTEM_ENABLED=False
            - BACKEND_API_HOST=backend-api
            - BACKEND_API_PORT=8000
        volumes:
          - ./credentials.yml:/home/dashboard/credentials.yml
          - ./pages:/home/dashboard/frontend/pages
          - ./bots:/backend-api/bots
        networks:
            - emqx-bridge
      backend-api:
        container_name: backend-api
        image: hummingbot/backend-api:latest
        ports:
          - "8000:8000"
        volumes:
          - ./bots:/backend-api/bots
          - /var/run/docker.sock:/var/run/docker.sock
        env_file:
          - .env
        environment:
          - BROKER_HOST=emqx
          - BROKER_PORT=1883
        networks:
          - emqx-bridge
      emqx:
        container_name: hummingbot-broker
        image: emqx:5
        restart: unless-stopped
        environment:
          - EMQX_NAME=emqx
          - EMQX_HOST=node1.emqx.local
          - EMQX_CLUSTER__DISCOVERY_STRATEGY=static
          - EMQX_CLUSTER__STATIC__SEEDS=[emqx@node1.emqx.local]
          - EMQX_LOADED_PLUGINS="emqx_recon,emqx_retainer,emqx_management,emqx_dashboard"
        volumes:
          - emqx-data:/opt/emqx/data
          - emqx-log:/opt/emqx/log
          - emqx-etc:/opt/emqx/etc
        ports:
          - "1883:1883"  # mqtt:tcp
          - "8883:8883"  # mqtt:tcp:ssl
          - "8083:8083"  # mqtt:ws
          - "8084:8084"  # mqtt:ws:ssl
          - "8081:8081"  # http:management
          - "18083:18083"  # http:dashboard
          - "61613:61613"  # web-stomp gateway
        networks:
          emqx-bridge:
            aliases:
              - node1.emqx.local
        healthcheck:
          test: [ "CMD", "/opt/emqx/bin/emqx_ctl", "status" ]
          interval: 5s
          timeout: 25s
          retries: 5

    networks:
      emqx-bridge:
        driver: bridge

    volumes:
      emqx-data: { }
      emqx-log: { }
      emqx-etc: { }
    ```
  </details>

- Add the following to `permissions.py` in your `deploy/pages` folder between the brackets inside `def public_pages()`:
  ```py
  Section("Emerald Fund", "💚"),
  Page("frontend/pages/config/emeraldfund/app_pmm.py", "PMM", "💚"),
  Page(
      "frontend/pages/config/emeraldfund/app_directional.py", "Directional", "💚"
  ),
  ```
  <details>
  <summary>Full example</summary>

  ```py
  from st_pages import Page, Section


  def main_page():
    return [Page("main.py", "Hummingbot Dashboard", "📊")]


  def public_pages():
    return [
        Section("Config Generator", "🎛️"),
        Page("frontend/pages/config/pmm_simple/app.py", "PMM Simple", "👨‍🏫"),
        Page("frontend/pages/config/pmm_dynamic/app.py", "PMM Dynamic", "👩‍🏫"),
        Page("frontend/pages/config/dman_maker_v2/app.py", "D-Man Maker V2", "🤖"),
        Page("frontend/pages/config/bollinger_v1/app.py", "Bollinger V1", "📈"),
        Page("frontend/pages/config/macd_bb_v1/app.py", "MACD_BB V1", "📊"),
        Page("frontend/pages/config/supertrend_v1/app.py", "SuperTrend V1", "👨‍🔬"),
        Page("frontend/pages/config/xemm_controller/app.py", "XEMM Controller", "⚡️"),
        Section("Emerald Fund", "💚"),
        Page("frontend/pages/config/emeraldfund/app_pmm.py", "PMM", "💚"),
        Page(
            "frontend/pages/config/emeraldfund/app_directional.py", "Directional", "💚"
        ),
        Section("Data", "💾"),
        Page("frontend/pages/data/download_candles/app.py", "Download Candles", "💹"),
        Section("Community Pages", "👨‍👩‍👧‍👦"),
        Page("frontend/pages/data/token_spreads/app.py", "Token Spreads", "🧙"),
        Page("frontend/pages/data/tvl_vs_mcap/app.py", "TVL vs Market Cap", "🦉"),
    ]


  def private_pages():
    return [
        Section("Bot Orchestration", "🐙"),
        Page("frontend/pages/orchestration/instances/app.py", "Instances", "🦅"),
        Page("frontend/pages/orchestration/launch_bot_v2/app.py", "Deploy V2", "🚀"),
        Page("frontend/pages/orchestration/credentials/app.py", "Credentials", "🔑"),
        Page("frontend/pages/orchestration/portfolio/app.py", "Portfolio", "💰"),
    ]
  ```
  </details>

- Run `docker compose up -d` to recreate the containers with the updated configuration, and the emerald fund should be in your dashboard now!
- You can play with some [examples from here](example_strategies/). When pasting examples, make sure to hit ctrl+enter (cmd+enter on Mac) to load the new code!
- Last but not least - Have fun! And if you make money, remember, think of how many people you can help with your gains, rather than how many sports cars you can buy. Trust me, its much more fulfilling!

# Coming soon 👀

- Full-AI assistant: Assist in creation, optimization, and backtesting, as well as correct mistakes and propose updated strategies based on findings during backtesting
    - Training EmeraldFundLlama is expensive! All the data and models are in-house made with a custom dataset and training happens on my own budget, a lot of manual labour to automate the rest. [Please consider subscribing to my patreon and you will get early access to the models](https://www.patreon.com/emerald_show).

# Support / contribute

- Feel free to [join my Discord server](https://discord.gg/dCjH8zZXuM), we can chat!
- I'm open for feedback and contributions, feel free to join in!
- Financial contributions are welcome on my patreon, you'll get exclusive access to early content + a special role on my server 💚

# Thanks

- dardonacci and fengtality for showing me the Dashboard and giving me a crash course
- dardonacci for answering all my questions I had during the development. It would otherwise not have been possible

# Sister projects

- [Hummingbot Discord Bot](https://github.com/peterwilli/HummingDiscordBot)
