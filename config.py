from dataclasses import dataclass
from environs import Env

@dataclass
class BotConfig:
    token: str

@dataclass
class InstagramConfig:
    rapidapi_key: str
    rapidapi_host: str
    follower_count: int = 50

@dataclass
class Config:
    bot: BotConfig
    instagram: InstagramConfig

def load_config():
    env = Env()
    env.read_env()

    return Config(
        bot=BotConfig(
            token=env.str("BOT_TOKEN"),
        ),
        instagram=InstagramConfig(
            rapidapi_key=env.str("RAPIDAPI_KEY", "532d0e9edemsh5566c31aceb7163p1343e7jsn11577b0723dd"),
            rapidapi_host=env.str("RAPIDAPI_HOST", "rocketapi-for-developers.p.rapidapi.com"),
            follower_count=env.int("DEFAULT_FOLLOWER_COUNT", 50)
        )
    )