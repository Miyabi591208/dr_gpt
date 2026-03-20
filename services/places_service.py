import math
from urllib.parse import quote_plus

import requests

GENRE_TO_PLACE_TYPES = {
    "ラーメン": ["ramen_restaurant"],
    "カフェ": ["cafe"],
    "焼肉": ["barbecue_restaurant"],
    "和食": ["japanese_restaurant"],
    "居酒屋": ["izakaya_restaurant"],
    "寿司": ["sushi_restaurant"],
}

# OSM / Overpass 用のざっくりした対応
GENRE_TO_OSM_FILTERS = {
    "ラーメン": {
        "amenities": ["restaurant", "fast_food"],
        "cuisines": ["ramen", "noodle"],
    },
    "カフェ": {
        "amenities": ["cafe"],
        "cuisines": [],
    },
    "焼肉": {
        "amenities": ["restaurant"],
        "cuisines": ["bbq", "barbecue", "japanese"],
    },
    "和食": {
        "amenities": ["restaurant"],
        "cuisines": ["japanese"],
    },
    "居酒屋": {
        "amenities": ["restaurant", "bar", "pub"],
        "cuisines": ["japanese"],
    },
    "寿司": {
        "amenities": ["restaurant"],
        "cuisines": ["sushi", "japanese"],
    },
}

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


class PlacesService:
    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "dr_gpt/1.0 (restaurant-search fallback; contact via app operator)"
            }
        )

    def search_nearby_shops(
        self,
        latitude: float,
        longitude: float,
        genre: str,
        budget: str,
        radius_meters: int = 1200,
        max_results: int = 5,
    ) -> list[dict]:
        """
        1) Google Places API を優先
        2) 失敗または 0件なら OSM Overpass API にフォールバック
        """
        google_error = None

        if self.api_key:
            try:
                google_places = self._search_nearby_shops_google(
                    latitude=latitude,
                    longitude=longitude,
                    genre=genre,
                    budget=budget,
                    radius_meters=radius_meters,
                    max_results=max_results,
                )
                if google_places:
                    return google_places
            except Exception as e:
                google_error = e

        osm_places = self._search_nearby_shops_osm(
            latitude=latitude,
            longitude=longitude,
            genre=genre,
            radius_meters=radius_meters,
            max_results=max_results,
        )
        if osm_places:
            return osm_places

        if google_error:
            raise RuntimeError(
                f"Google Places API でも OSM フォールバックでも候補を取得できませんでした: {google_error}"
            )

        raise RuntimeError("候補店舗を取得できませんでした。")

    def _search_nearby_shops_google(
        self,
        latitude: float,
        longitude: float,
        genre: str,
        budget: str,
        radius_meters: int,
        max_results: int,
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

        response = self.session.post(url, json=body, headers=headers, timeout=20)
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
                    "distance_m": self._distance_m(latitude, longitude, lat, lng)
                    if lat is not None and lng is not None
                    else None,
                    "source": "google_places",
                }
            )

        places.sort(
            key=lambda x: (
                x.get("distance_m") is None,
                x.get("distance_m") or 10**9,
                -(x.get("rating") or 0),
            )
        )
        return places[:max_results]

    def _search_nearby_shops_osm(
        self,
        latitude: float,
        longitude: float,
        genre: str,
        radius_meters: int,
        max_results: int,
    ) -> list[dict]:
        filters = GENRE_TO_OSM_FILTERS.get(
            genre,
            {"amenities": ["restaurant", "cafe", "fast_food"], "cuisines": []},
        )

        amenity_regex = "|".join(filters["amenities"]) if filters["amenities"] else "restaurant|cafe|fast_food"
        cuisine_regex = "|".join(filters["cuisines"])

        query = f"""
[out:json][timeout:20];
(
  node(around:{int(radius_meters)},{latitude},{longitude})["amenity"~"^({amenity_regex})$"];
  way(around:{int(radius_meters)},{latitude},{longitude})["amenity"~"^({amenity_regex})$"];
  relation(around:{int(radius_meters)},{latitude},{longitude})["amenity"~"^({amenity_regex})$"];
);
out center tags;
"""

        response = self.session.post(
            OVERPASS_URL,
            data=query.encode("utf-8"),
            headers={"Content-Type": "text/plain; charset=utf-8"},
            timeout=25,
        )
        response.raise_for_status()
        data = response.json()

        places = []
        seen = set()

        for element in data.get("elements", []):
            tags = element.get("tags", {}) or {}
            name = (tags.get("name") or "").strip()
            if not name:
                continue

            amenity = (tags.get("amenity") or "").strip().lower()
            cuisine = (tags.get("cuisine") or "").strip().lower()

            if cuisine_regex:
                cuisine_parts = {c.strip() for c in cuisine.replace(";", ",").split(",") if c.strip()}
                if cuisine_parts and not any(c in cuisine_parts for c in filters["cuisines"]):
                    # cuisineが明記されていて、かつ目的ジャンルとズレる場合だけ除外
                    pass

            lat = element.get("lat")
            lng = element.get("lon")

            if lat is None or lng is None:
                center = element.get("center", {})
                lat = center.get("lat")
                lng = center.get("lon")

            if lat is None or lng is None:
                continue

            address = self._build_osm_address(tags)
            key = (name, round(lat, 6), round(lng, 6))
            if key in seen:
                continue
            seen.add(key)

            distance_m = self._distance_m(latitude, longitude, lat, lng)

            google_maps_uri = self.build_search_url(name=name, address=address)

            places.append(
                {
                    "name": name,
                    "address": address or "住所不明",
                    "lat": lat,
                    "lng": lng,
                    "rating": None,
                    "reviews": None,
                    "google_maps_uri": google_maps_uri,
                    "price_level": None,
                    "id": f"osm-{element.get('type', 'element')}-{element.get('id')}",
                    "distance_m": distance_m,
                    "source": "osm_fallback",
                    "amenity": amenity,
                    "cuisine": cuisine,
                }
            )

        places.sort(
            key=lambda x: (
                x.get("distance_m") is None,
                x.get("distance_m") or 10**9,
                x.get("name", ""),
            )
        )
        return places[:max_results]

    @staticmethod
    def _build_osm_address(tags: dict) -> str:
        parts = [
            tags.get("addr:postcode"),
            tags.get("addr:state"),
            tags.get("addr:province"),
            tags.get("addr:city"),
            tags.get("addr:suburb"),
            tags.get("addr:quarter"),
            tags.get("addr:neighbourhood"),
            tags.get("addr:street"),
            tags.get("addr:housenumber"),
        ]
        parts = [p for p in parts if p]
        return " ".join(parts).strip()

    @staticmethod
    def _match_budget(price_level: str | None, budget: str) -> bool:
        if not price_level:
            return True

        mapping = {
            "〜1000円": {"PRICE_LEVEL_INEXPENSIVE"},
            "1000〜3000円": {"PRICE_LEVEL_INEXPENSIVE", "PRICE_LEVEL_MODERATE"},
            "3000円以上": {
                "PRICE_LEVEL_MODERATE",
                "PRICE_LEVEL_EXPENSIVE",
                "PRICE_LEVEL_VERY_EXPENSIVE",
            },
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
    def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        r = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lng2 - lng1)

        a = (
            math.sin(d_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(r * c, 1)

    @staticmethod
    def build_directions_url(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> str:
        origin = quote_plus(f"{origin_lat},{origin_lng}")
        dest = quote_plus(f"{dest_lat},{dest_lng}")
        return f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={dest}&travelmode=walking"

    @staticmethod
    def build_search_url(name: str, address: str) -> str:
        query = quote_plus(f"{name} {address}".strip())
        return f"https://www.google.com/maps/search/?api=1&query={query}"
