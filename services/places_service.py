import requests
from urllib.parse import quote_plus


GENRE_TO_PLACE_TYPES = {
    "ラーメン": ["ramen_restaurant"],
    "カフェ": ["cafe"],
    "焼肉": ["barbecue_restaurant"],
    "和食": ["japanese_restaurant"],
    "居酒屋": ["izakaya_restaurant"],
    "寿司": ["sushi_restaurant"],
}


class PlacesService:
    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def search_nearby_shops(
        self,
        latitude: float,
        longitude: float,
        genre: str,
        budget: str,
        radius_meters: int = 1200,
        max_results: int = 5,
    ) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("GOOGLE_MAPS_API_KEY が未設定です。")

        included_types = GENRE_TO_PLACE_TYPES.get(genre, ["restaurant"])

        url = "https://places.googleapis.com/v1/places:searchNearby"
        body = {
            "includedTypes": included_types,
            "maxResultCount": max_results,
            "rankPreference": "DISTANCE",
            "languageCode": "ja",
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": float(radius_meters),
                }
            },
        }

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": ",".join(
                [
                    "places.displayName",
                    "places.formattedAddress",
                    "places.location",
                    "places.rating",
                    "places.userRatingCount",
                    "places.googleMapsUri",
                    "places.priceLevel",
                    "places.id",
                ]
            ),
        }

        response = requests.post(url, json=body, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()

        places = []
        for p in data.get("places", []):
            name = p.get("displayName", {}).get("text", "名称不明")
            address = p.get("formattedAddress", "住所不明")
            loc = p.get("location", {})
            lat = loc.get("latitude")
            lng = loc.get("longitude")
            rating = p.get("rating")
            reviews = p.get("userRatingCount")
            google_maps_uri = p.get("googleMapsUri")
            price_level = p.get("priceLevel")

            if budget and not self._match_budget(price_level, budget):
                continue

            places.append(
                {
                    "name": name,
                    "address": address,
                    "lat": lat,
                    "lng": lng,
                    "rating": rating,
                    "reviews": reviews,
                    "google_maps_uri": google_maps_uri,
                    "price_level": price_level,
                    "id": p.get("id"),
                }
            )
        return places

    @staticmethod
    def _match_budget(price_level: str | None, budget: str) -> bool:
        if not price_level:
            return True

        mapping = {
            "〜1000円": {"PRICE_LEVEL_INEXPENSIVE"},
            "1000〜3000円": {"PRICE_LEVEL_INEXPENSIVE", "PRICE_LEVEL_MODERATE"},
            "3000円以上": {"PRICE_LEVEL_MODERATE", "PRICE_LEVEL_EXPENSIVE", "PRICE_LEVEL_VERY_EXPENSIVE"},
            "こだわらない": {
                "PRICE_LEVEL_INEXPENSIVE",
                "PRICE_LEVEL_MODERATE",
                "PRICE_LEVEL_EXPENSIVE",
                "PRICE_LEVEL_VERY_EXPENSIVE",
            },
        }
        allowed = mapping.get(budget, set())
        return (not allowed) or (price_level in allowed)

    @staticmethod
    def build_directions_url(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> str:
        origin = quote_plus(f"{origin_lat},{origin_lng}")
        dest = quote_plus(f"{dest_lat},{dest_lng}")
        return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={dest}&travelmode=walking"

    @staticmethod
    def build_search_url(name: str, address: str) -> str:
        query = quote_plus(f"{name} {address}")
        return f"https://www.google.com/maps/search/?api=1&query={query}"