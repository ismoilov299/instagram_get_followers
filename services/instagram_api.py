import json
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from aiohttp import ClientSession


class InstagramAPI:
    def __init__(self, api_key: str, api_host: str, session_pool_size: int = 5):
        self.api_key = api_key
        self.api_host = api_host
        self.base_url = f"https://{api_host}"
        self.headers = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': api_host,
            'Content-Type': "application/json"
        }
        # Создаем общий пул соединений для повторного использования
        self.session_pool_size = session_pool_size
        self._session = None
        self._rate_limit_retry_count = 3  # Количество повторных попыток при ошибке API
        self._connection_timeout = aiohttp.ClientTimeout(total=30, connect=15)

    async def _get_session(self) -> ClientSession:
        """Получить или создать пул сессий для повторного использования соединений"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=self.session_pool_size, force_close=False)
            self._session = aiohttp.ClientSession(connector=connector, timeout=self._connection_timeout)
        return self._session

    async def close(self):
        """Закрыть сессию при завершении работы"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/instagram/user/get_info"
        payload = json.dumps({"username": username})

        session = await self._get_session()
        try:
            async with session.post(url, headers=self.headers, data=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    user = data["response"]["body"]["data"]["user"]
                    return {
                        "id": user["id"],
                        "username": username,
                        "full_name": user.get("full_name", ""),
                        "followers_count": user["edge_followed_by"]["count"],
                        "following_count": user["edge_follow"]["count"],
                        "posts_count": user["edge_owner_to_timeline_media"]["count"],
                        "bio": user.get("biography", "")
                    }
                else:
                    print(f"API error: {response.status} - {await response.text()}")
                    return None
        except Exception as e:
            print(f"Xatolik: {e}")
            return None

    async def get_user_followers(self, user_id: str, count: int = 50) -> List[Dict[str, str]]:
        url = f"{self.base_url}/instagram/user/get_followers"
        payload = json.dumps({
            "id": user_id,
            "count": count,
            "max_id": None
        })

        session = await self._get_session()
        try:
            async with session.post(url, headers=self.headers, data=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    followers = []

                    for user in data["response"]["body"]["users"]:
                        if "username" in user:
                            followers.append({
                                "username": user["username"],
                                "id": user["id"],
                                "link": f"https://www.instagram.com/{user['username']}"
                            })

                    return followers
                else:
                    print(f"API error: {response.status} - {await response.text()}")
                    return []
        except Exception as e:
            print(f"Xatolik: {e}")
            return []

    async def get_user_followers_batch(self, user_id: str, count: int = 100, max_id: str = None) -> Dict[str, Any]:
        """
        Оптимизированная версия получения пакета подписчиков с встроенным механизмом повторных попыток

        Args:
            user_id: Instagram user ID
            count: Number of followers to fetch (default: 100)
            max_id: Pagination token for the next batch (default: None)

        Returns:
            dict: Contains 'followers' list and 'next_max_id' for pagination
        """
        url = f"{self.base_url}/instagram/user/get_followers"
        payload = json.dumps({
            "id": user_id,
            "count": count,
            "max_id": max_id
        })

        # Получаем сессию из пула
        session = await self._get_session()

        # Реализуем механизм повторных попыток для надежности
        for attempt in range(self._rate_limit_retry_count + 1):
            try:
                async with session.post(url, headers=self.headers, data=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        followers = []

                        for user in data["response"]["body"]["users"]:
                            if "username" in user:
                                followers.append({
                                    "username": user["username"],
                                    "id": user["id"],
                                    "link": f"https://www.instagram.com/{user['username']}"
                                })

                        # Extract next_max_id from the response for pagination
                        next_max_id = None
                        if "next_max_id" in data["response"]["body"]:
                            next_max_id = data["response"]["body"]["next_max_id"]

                        return {
                            "followers": followers,
                            "next_max_id": next_max_id
                        }
                    elif response.status == 429:  # Rate limit exceeded
                        if attempt < self._rate_limit_retry_count:
                            # Экспоненциальная задержка: 2, 4, 8 секунд...
                            backoff_time = 2 ** attempt
                            print(f"Rate limit exceeded. Retrying in {backoff_time} seconds...")
                            await asyncio.sleep(backoff_time)
                            continue
                        else:
                            print(f"Rate limit exceeded after {attempt + 1} attempts")
                            return {"followers": [], "next_max_id": None}
                    else:
                        print(f"API error: {response.status} - {await response.text()}")
                        # При других ошибках тоже пробуем повторить
                        if attempt < self._rate_limit_retry_count:
                            await asyncio.sleep(2)
                            continue
                        return {"followers": [], "next_max_id": None}
            except asyncio.TimeoutError:
                print(f"Timeout error (attempt {attempt + 1}/{self._rate_limit_retry_count + 1})")
                if attempt < self._rate_limit_retry_count:
                    await asyncio.sleep(2)
                    continue
                return {"followers": [], "next_max_id": None}
            except Exception as e:
                print(f"Unexpected error fetching followers: {e}")
                if attempt < self._rate_limit_retry_count:
                    await asyncio.sleep(2)
                    continue
                return {"followers": [], "next_max_id": None}

        # В случае исчерпания всех попыток
        return {"followers": [], "next_max_id": None}

    async def get_multiple_batches(self, user_id: str, count: int, max_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Получить несколько партий подписчиков параллельно

        Args:
            user_id: Instagram user ID
            count: Number of followers per batch
            max_ids: List of pagination tokens

        Returns:
            List of batch results
        """
        # Создаем задачи для параллельного выполнения
        tasks = [
            self.get_user_followers_batch(user_id, count, max_id)
            for max_id in max_ids
        ]

        # Выполняем задачи параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Фильтруем ошибки и возвращаем результаты
        return [r for r in results if not isinstance(r, Exception) and r.get('followers')]