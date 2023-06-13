# YeloBot

This is the source code of YeloBot. Check out bot.py for the entry point of the bot.

## Contributing

If you would like to contribute and need to run the bot locally for development purposes, you will need to create a Discord bot and a free MongoDB database. Both of these are pretty easy! See how to create a Discord bot [here](https://discord.com/developers/docs/getting-started). For the MongoDB database, go to the [MongoDB website](https://www.mongodb.com/) and create a free cluster through their UI and a database inside of that cluster.

To get the bot running, you will need to set a few environment variables. Instead of actually setting these variables on your system, you can use a .env file. Simply create a file called ".env" **(no file name, just this extension)** in the root directory of this project. Here is a template for what this file should look like. If you don't need a variable for your purposes, simply leave it blank.

```
######### Required #########

# The Discord bot token.
BOT_TOKEN=
# Your MongoDB username
MONGO_USER=
# The name of your MongoDB project
MONGO_PROJECT=
# The name of your MongoDB database
MONGO_DATABASE=
# Your MongoDB password
MONGO_PW=

######### Optional #########
# Some commands/features won't work without these,
# but the bot should still run fine.

# Steam API key
STEAM_KEY=
# OpenWeatherMap API key (required for +weather to work)
WEATHER_KEY=
# TimezoneDB key (required for +time to work)
TIMEZONE_KEY=
# Scripture bible API key (required for daily bible verses) from here https://scripture.api.bible/
BIBLE_API_KEY=

######### Rarely Needed #########
# These are used by YeloBot's live deployment, but for
# development or testing purposes, they are rarely needed.

# IP address for the Club Cheadle Minecraft server
MINECRAFT_IP=
# RCON password for the Club Cheadle Minecraft server
RCONPW=
# Hostname for Club Cheadle Minecraft server (generally used for domains)
MINECRAFT_HOST=
# OpenAI API key for YeloBot's natural language features
OPENAI_API_KEY=
```

YeloBot currently runs on **Python 3.11**. There are a lot of dependencies, so I **strongly** recommend creating a virtual environment before running it. To do this, run `python -m venv [SOME_ENVIRONMENT_NAME]`. Then, activate it using `[SOME_ENVIRONMENT_NAME]\Scripts\activate` on Windows or `source [SOME_ENVIRONMENT_NAME]/bin/activate` on Mac/Linux. You will then be able to install all of the dependencies on this virtual environment with `python -m pip install -r requirements.txt`.

After you've done all that, you're finally ready to run the bot with `python bot.py`. If you've read this whole section, thank you for at least considering making a contribution to YeloBot :)