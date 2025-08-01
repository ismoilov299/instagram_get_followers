import json
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Callable
from aiohttp import ClientSession


class InstagramAPI:
    def __init__(self, api_key: str, api_host: str = "instagram-social-api.p.rapidapi.com", session_pool_size: int = 5):
        self.api_key = api_key
        self.api_host = api_host
        self.base_url = f"https://{api_host}"
        self.headers = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': api_host
        }
        # Session pool setup
        self.session_pool_size = session_pool_size
        self._session = None
        self._rate_limit_retry_count = 3
        self._connection_timeout = aiohttp.ClientTimeout(total=30, connect=15)

    async def _get_session(self) -> ClientSession:
        """Get or create session pool for connection reuse"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(limit=self.session_pool_size, force_close=False)
            self._session = aiohttp.ClientSession(connector=connector, timeout=self._connection_timeout)
        return self._session

    async def close(self):
        """Close session on shutdown"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Get Instagram user info using Instagram Social API

        Args:
            username: Instagram username (without @)

        Returns:
            Dict with user info or None if error
        """
        url = f"{self.base_url}/v1/info"
        params = {"username_or_id_or_url": username}

        session = await self._get_session()
        try:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()

                    # Instagram Social API response structure
                    if "data" in data:
                        user = data["data"]
                        return {
                            "id": str(user.get("id", "")),
                            "username": user.get("username", username),
                            "full_name": user.get("full_name", ""),
                            "followers_count": user.get("follower_count", 0),
                            "following_count": user.get("following_count", 0),
                            "posts_count": user.get("media_count", 0),
                            "bio": user.get("biography", ""),
                            "is_verified": user.get("is_verified", False),
                            "is_private": user.get("is_private", False),
                            "profile_pic_url": user.get("profile_pic_url", ""),
                            "external_url": user.get("external_url", "")
                        }
                    else:
                        print(f"API response error: {data}")
                        return None

                elif response.status == 404:
                    print(f"User {username} not found")
                    return None
                else:
                    error_text = await response.text()
                    print(f"API error: {response.status} - {error_text}")
                    return None

        except asyncio.TimeoutError:
            print(f"Timeout error for user {username}")
            return None
        except Exception as e:
            print(f"Unexpected error getting user info for {username}: {e}")
            return None

    async def get_user_followers(self, username_or_id: str, count: int = 50) -> List[Dict[str, str]]:
        """
        Get user followers using Instagram Social API

        Args:
            username_or_id: Instagram username or user ID
            count: Number of followers (note: API returns ~50 per request regardless)

        Returns:
            List of follower dictionaries
        """
        url = f"{self.base_url}/v1/followers"
        params = {"username_or_id_or_url": username_or_id}

        session = await self._get_session()
        try:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    followers = []

                    if "data" in data and "items" in data["data"]:
                        for user in data["data"]["items"]:
                            if user.get("username"):  # Only add users with valid usernames
                                followers.append({
                                    "username": user.get("username", ""),
                                    "id": str(user.get("id", "")),
                                    "full_name": user.get("full_name", ""),
                                    "link": f"https://www.instagram.com/{user.get('username', '')}",
                                    "is_verified": user.get("is_verified", False),
                                    "is_private": user.get("is_private", False),
                                    "profile_pic_url": user.get("profile_pic_url", "")
                                })

                    return followers
                else:
                    error_text = await response.text()
                    print(f"API error getting followers: {response.status} - {error_text}")
                    return []

        except Exception as e:
            print(f"Error getting followers: {e}")
            return []

    async def get_user_followers_batch(self, username_or_id: str, count: int = 100, pagination_token: str = None) -> \
    Dict[str, Any]:
        """
        Get a batch of followers with pagination support

        Args:
            username_or_id: Instagram username or user ID
            count: Number of followers (note: API returns ~50 per request regardless)
            pagination_token: Token for pagination

        Returns:
            Dict with 'followers' list and 'next_max_id' for pagination
        """
        url = f"{self.base_url}/v1/followers"
        params = {"username_or_id_or_url": username_or_id}

        # Add pagination token if provided
        if pagination_token:
            params["pagination_token"] = pagination_token

        session = await self._get_session()

        # Retry mechanism for reliability
        for attempt in range(self._rate_limit_retry_count + 1):
            try:
                async with session.get(url, headers=self.headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        followers = []

                        if "data" in data and "items" in data["data"]:
                            for user in data["data"]["items"]:
                                if user.get("username"):  # Only add users with valid usernames
                                    followers.append({
                                        "username": user.get("username", ""),
                                        "id": str(user.get("id", "")),
                                        "full_name": user.get("full_name", ""),
                                        "link": f"https://www.instagram.com/{user.get('username', '')}",
                                        "is_verified": user.get("is_verified", False),
                                        "is_private": user.get("is_private", False),
                                        "profile_pic_url": user.get("profile_pic_url", "")
                                    })

                            # Extract pagination_token for next batch
                            next_pagination_token = data.get("pagination_token")

                            return {
                                "followers": followers,
                                "next_max_id": next_pagination_token,  # Keep this name for compatibility
                                "has_more": bool(next_pagination_token),
                                "count": len(followers)
                            }
                        else:
                            return {
                                "followers": [],
                                "next_max_id": None,
                                "has_more": False,
                                "count": 0
                            }

                    elif response.status == 429:  # Rate limit exceeded
                        if attempt < self._rate_limit_retry_count:
                            backoff_time = 2 ** attempt
                            print(f"Rate limit exceeded. Retrying in {backoff_time} seconds...")
                            await asyncio.sleep(backoff_time)
                            continue
                        else:
                            print(f"Rate limit exceeded after {attempt + 1} attempts")
                            return {"followers": [], "next_max_id": None, "has_more": False, "count": 0}

                    elif response.status == 404:
                        print(f"User {username_or_id} not found")
                        return {"followers": [], "next_max_id": None, "has_more": False, "count": 0}

                    else:
                        error_text = await response.text()
                        print(f"API error: {response.status} - {error_text}")
                        if attempt < self._rate_limit_retry_count:
                            await asyncio.sleep(2)
                            continue
                        return {"followers": [], "next_max_id": None, "has_more": False, "count": 0}

            except asyncio.TimeoutError:
                print(f"Timeout error (attempt {attempt + 1}/{self._rate_limit_retry_count + 1})")
                if attempt < self._rate_limit_retry_count:
                    await asyncio.sleep(2)
                    continue
                return {"followers": [], "next_max_id": None, "has_more": False, "count": 0}

            except Exception as e:
                print(f"Unexpected error fetching followers: {e}")
                if attempt < self._rate_limit_retry_count:
                    await asyncio.sleep(2)
                    continue
                return {"followers": [], "next_max_id": None, "has_more": False, "count": 0}

        return {"followers": [], "next_max_id": None, "has_more": False, "count": 0}

    async def get_multiple_batches(self, username_or_id: str, count: int, pagination_tokens: List[str]) -> List[
        Dict[str, Any]]:
        """
        Get multiple batches of followers in parallel

        Args:
            username_or_id: Instagram username or user ID
            count: Number of followers per batch
            pagination_tokens: List of pagination tokens

        Returns:
            List of batch results
        """
        if not pagination_tokens:
            return []

        tasks = [
            self.get_user_followers_batch(username_or_id, count, pagination_token)
            for pagination_token in pagination_tokens
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid_results = []

        for result in results:
            if not isinstance(result, Exception) and result.get('followers'):
                valid_results.append(result)
            elif isinstance(result, Exception):
                print(f"Exception in batch request: {result}")

        return valid_results

    async def get_all_followers_with_progress(
            self,
            username_or_id: str,
            progress_callback: Optional[Callable] = None,
            max_followers: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get all followers with progress tracking and optional limit

        Args:
            username_or_id: Instagram username or user ID
            progress_callback: Function to call with progress updates (current_count, estimated_total, batch_count)
            max_followers: Maximum number of followers to fetch (None for all)

        Returns:
            List of all followers up to the specified limit
        """
        all_followers = []
        pagination_token = None
        batch_count = 0

        while True:
            batch_count += 1

            # Call progress callback if provided
            if progress_callback:
                try:
                    await progress_callback(len(all_followers), max_followers, batch_count)
                except Exception as e:
                    print(f"Error in progress callback: {e}")

            # Get next batch
            batch_result = await self.get_user_followers_batch(
                username_or_id=username_or_id,
                count=50,  # This API returns ~50 per batch
                pagination_token=pagination_token
            )

            # Check if we got any followers
            if not batch_result or not batch_result.get('followers'):
                print(f"No more followers found after {batch_count} batches")
                break

            # Add followers to our list
            new_followers = batch_result.get('followers', [])

            # Check if we would exceed the max_followers limit
            if max_followers:
                remaining_slots = max_followers - len(all_followers)
                if remaining_slots <= 0:
                    break
                if len(new_followers) > remaining_slots:
                    new_followers = new_followers[:remaining_slots]

            all_followers.extend(new_followers)

            # Check if we've reached our limit
            if max_followers and len(all_followers) >= max_followers:
                print(f"Reached follower limit of {max_followers}")
                break

            # Get pagination token for next batch
            pagination_token = batch_result.get('next_max_id')

            # If no pagination token, we're done
            if not pagination_token or not batch_result.get('has_more', False):
                print(f"Reached end of followers list after {batch_count} batches")
                break

            # Add small delay to be respectful to the API
            await asyncio.sleep(0.5)

            # Safety limit to prevent infinite loops (2000 batches = ~100k followers)
            if batch_count > 2000:
                print(f"Reached safety limit of {batch_count} batches")
                break

        print(f"Total followers fetched: {len(all_followers)} in {batch_count} batches")
        return all_followers

    async def get_user_following(self, username_or_id: str) -> List[Dict[str, str]]:
        """
        Get users that the specified user is following

        Args:
            username_or_id: Instagram username or user ID

        Returns:
            List of following users (if endpoint exists)
        """
        # Note: Check if this endpoint exists in the API documentation
        url = f"{self.base_url}/v1/following"
        params = {"username_or_id_or_url": username_or_id}

        session = await self._get_session()
        try:
            async with session.get(url, headers=self.headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    following = []

                    if "data" in data and "items" in data["data"]:
                        for user in data["data"]["items"]:
                            if user.get("username"):
                                following.append({
                                    "username": user.get("username", ""),
                                    "id": str(user.get("id", "")),
                                    "full_name": user.get("full_name", ""),
                                    "link": f"https://www.instagram.com/{user.get('username', '')}",
                                    "is_verified": user.get("is_verified", False),
                                    "is_private": user.get("is_private", False)
                                })

                    return following
                else:
                    print(f"Following endpoint may not be available: {response.status}")
                    return []

        except Exception as e:
            print(f"Error getting following list: {e}")
            return []

    async def health_check(self) -> bool:
        """
        Check if the API is working properly

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Test with a known public account
            test_result = await self.get_user_info("instagram")
            return test_result is not None
        except Exception as e:
            print(f"Health check failed: {e}")
            return False

    def get_api_info(self) -> Dict[str, str]:
        """
        Get information about the current API configuration

        Returns:
            Dict with API information
        """
        return {
            "api_host": self.api_host,
            "base_url": self.base_url,
            "has_api_key": bool(self.api_key),
            "session_pool_size": self.session_pool_size,
            "retry_count": self._rate_limit_retry_count
        }