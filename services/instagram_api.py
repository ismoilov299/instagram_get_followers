import json
import aiohttp
from typing import Dict, List, Optional, Any


class InstagramAPI:
    def __init__(self, api_key: str, api_host: str):
        self.api_key = api_key
        self.api_host = api_host
        self.base_url = f"https://{api_host}"
        self.headers = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': api_host,
            'Content-Type': "application/json"
        }

    async def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}/instagram/user/get_info"
        payload = json.dumps({"username": username})

        async with aiohttp.ClientSession() as session:
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
                        return None
            except Exception as e:
                print(f"Xatolik: {e}")
                return None

    async def get_user_followers(self, user_id: str, count: int = 12) -> List[Dict[str, str]]:
        url = f"{self.base_url}/instagram/user/get_followers"
        payload = json.dumps({
            "id": user_id,
            "count": count,
            "max_id": None
        })

        async with aiohttp.ClientSession() as session:
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
                        return []
            except Exception as e:
                print(f"Xatolik: {e}")
                return []