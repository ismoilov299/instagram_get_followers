from dataclasses import dataclass
from environs import Env
from typing import Optional


@dataclass
class TelegramConfig:
    token: str


@dataclass
class InstagramConfig:
    api_key: str
    api_host: str
    follower_count: int = 50


@dataclass
class Config:
    telegram: TelegramConfig
    instagram: InstagramConfig


def load_config(path: Optional[str] = None) -> Config:
    env = Env()
    env.read_env(path)

    return Config(
        telegram=TelegramConfig(
            token=env.str("BOT_TOKEN"),
        ),
        instagram=InstagramConfig(
            api_key=env.str("RAPIDAPI_KEY"),
            api_host=env.str("RAPIDAPI_HOST"),
            follower_count=env.int("DEFAULT_FOLLOWER_COUNT", 50),
        ),
    )

