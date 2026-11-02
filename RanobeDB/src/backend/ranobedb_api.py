from anyio import Path
import httpx
from typing import Any
from .rate_limiter import async_rate_limit_pause

BASE_URL = "https://ranobedb.org/api/v0"
IMAGE_BASE_URL = "https://images.ranobedb.org"


@async_rate_limit_pause
async def get_image(filename: str) -> bytes:
    """
    Fetch an image from RanobeDB by filename.
    """
    img_url = f"{IMAGE_BASE_URL}/{filename}"
    async with httpx.AsyncClient() as client:
        img_response = await client.get(img_url, timeout=30)
        img_response.raise_for_status()
        return img_response.content


async def download_image(filename: str, dest_path: Path) -> str |None:
    """
    Download an image from RanobeDB and save it to the specified path.

    Args:
        filename (str): Image filename on RanobeDB.
        dest_path (Path): Local file path to save the image.
    """
    try:
        await dest_path.mkdir(parents=True, exist_ok=True)
        img_data = await get_image(filename)
        
        file_path = dest_path / filename
        await file_path.write_bytes(img_data)

        return str(file_path)
    except Exception as e:
        print(f"Error downloading image {filename}: {e}")
        return None


@async_rate_limit_pause
async def _get(path: str, params: dict[str, Any] | None = None) -> dict:
    """
    Internal ASYNC GET helper with rate limiting and error handling.

    Args:
        path (str): Endpoint path (e.g. "/series").
        params (dict[str, Any] | None): Query parameters.

    Returns:
        dict: JSON response from RanobeDB.
    """

    url = f"{BASE_URL}{path}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()


# ----- SERIES -----


async def get_series(q: str, **kwargs) -> dict:
    """
    Fetch a list of series filtered by query string.

    Required:
        q (str): Query string (e.g., title keyword)

    Optional:
        page: number
        limit: number
            Default 24; Max: 100
        pubStatus:: 'ongoing' | 'completed' | 'hiatus' | 'stalled' | 'cancelled' | 'unknown'
        genresInclude: number[]
        genresExclude: number[]
        tagsInclude: number[]
        tagsExclude: number[]
        til: 'and' | 'or'
            Tags include logic
        tel: 'and' | 'or'
            Tags exclude logic
        rl: Language[]
            Release lanuages
        rll: 'and' | 'or'
            Release lanuages logic
        rf: ('digital' | 'print' | 'audio')[]
            Release formats
        rfl: 'and' | 'or'
            Release formats logic
        staff: number[]
            The id of staff
        sl: 'and' | 'or'
            Staff logic
        p: number[]
            The id of publishers
        pl: 'and' | 'or'
            Publisher logic
        sort: 'Relevance desc' | 'Relevance asc' | 'Title asc' | 'Title desc' | 'Start date asc' | 'Start date desc' | 'End date asc' | 'End date desc' | 'Num. books asc' | 'Num. books desc'

    Returns:
        Dict: JSON response with series list

    JSON response structure:
        {
            series: {
                book: {
                    id: number;
                    image: {
                        id: number;
                        filename: string;
                        height: number;
                        nsfw: boolean;
                        spoiler: boolean;
                        width: number;
                    } | null;
                } | null;
                volumes: {
                    count: string | number | bigint;
                } | null;
                id: number;
                lang: "id" | "ja" | "en" | "zh-Hans" | "zh-Hant" | "fr" | "es" | "ko" | "ar" | "bg" | "ca" | "cs" | "ck" | "da" | "de" | ... 35 more
                romaji: string | null;
                hidden: boolean;
                locked: boolean;
                title: string;
                olang: "id" | "ja" | "en" | "zh-Hans" | "zh-Hant" | "fr" | "es" | "ko" | "ar" | "bg" | "ca" | "cs" | "ck" | "da" | "de" | ... 35 more
                c_num_books: number;
                title_orig: string | null;
                romaji_orig: string | null;
            }[];
            count: string;
            currentPage: number;
            totalPages: number;
        }
    """
    return await _get("/series", {"q": q, **kwargs})


async def get_series_by_id(series_id: int) -> dict:
    """
    Fetch a single series by ID.

    Args:
        series_id (int): RanobeDB series ID

    Returns:
        Dict: JSON response for that series

    JSON response structure:
        series:{
            id: number;
            lang: Language;
            romaji: string | null;
            title: string;
            hidden: boolean;
            locked: boolean;
            description: string;
            olang: Language;
            bookwalker_id: number | null;
            wikidata_id: number | null;
            aliases: string;
            publication_status: "unknown" | "ongoing" | "completed" | "hiatus" | "stalled" | "cancelled";
            anidb_id: number | null;
            start_date: number;
            end_date: number;
            web_novel: string | null;
            title_orig: string | null;
            romaji_orig: string | null;
            book_description: {
                description: string;
                description_ja: string;
            } | null;
            books: {
                book_type: "main" | "sub";
                sort_order: number;
                id: number;
                lang: Language;
                romaji: string | null;
                title: string;
                image_id: number | null;
                c_release_date: number;
                title_orig: string | null;
                romaji_orig: string | null;
                image: {
                    id: number;
                    filename: string;
                    height: number;
                    nsfw: boolean;
                    spoiler: boolean;
                    width: number;
                } | null;
            }[];
            titles: {
                lang: Language;
                romaji: string | null;
                official: true;
                title: string;
            }[];
            child_series: {
                id: number;
                relation_type: "prequel" | "sequel" | "side story" | "main story" | "spin-off" | "parent story" | "alternate version";
                lang: Language;
                romaji: string | null;
                title: string;
            }[];
            publishers: {
                id: number;
                romaji: string | null;
                name: string;
                publisher_type: "publisher" | "imprint";
                lang: Language;
            }[];
            staff: {
                role_type: "staff" | "author" | "artist" | "editor" | "translator" | "narrator";
                note: string;
                romaji: string | null;
                name: string;
                staff_id: number;
                lang: Language;
                staff_alias_id: number;
            }[];
            tags: {
                id: number;
                name: string;
                ttype: "content" | "demographic" | "genre" | "tag";
            }[];
        }
    """
    return await _get(f"/series/{series_id}")


# ----- BOOKS -----


async def get_books(q: str, **kwargs) -> dict:
    """
    Fetch a list of books filtered by query string.

    Required:
        q (str): Search query

    Optional:
        page: number
        limit: number
            Default 24; Max: 100
        rl: Language[]
            Release lanuages
        rll: 'and' | 'or'
            Release lanuages logic
        rf: ('digital' | 'print' | 'audio')[]
            Release formats
        rfl: 'and' | 'or'
            Release formats logic
        staff: number[]
            The id of staff
        sl: 'and' | 'or'
            Staff logic
        p: number[]
            The id of publishers
        pl: 'and' | 'or'
            Publisher logic
        sort: 'Relevance desc' | 'Relevance asc' | 'Title asc' | 'Title desc' | 'Release date asc' | 'Release date desc'

    Returns:
        Dict: JSON response with book list

    JSON response structure:
        {
            books:  {
                id: number;
                title: string;
                lang: Language;
                romaji: string | null;
                image_id: number | null;
                olang: Language;
                c_release_date: number;
                title_orig: string | null;
                romaji_orig: string | null;
                image: {
                    id: number;
                    filename: string;
                    height: number;
                    nsfw: boolean;
                    spoiler: boolean;
                    width: number;
                } | null;
            }[];
            count: string;
            currentPage: number;
            totalPages: number;
        }
    """
    return await _get("/books", {"q": q, **kwargs})


async def get_book_by_id(book_id: int) -> dict:
    """
    Fetch a book by its ID.

    Args:
        book_id (int): RanobeDB book ID

    Returns:
        Dict: JSON response

    JSON response structure:
        book: {
            description: string;
            lang: Language;
            id: number;
            romaji: string | null;
            description_ja: string;
            hidden: boolean;
            image_id: number | null;
            olang: Language;
            locked: boolean;
            c_release_date: number;
            title: string;
            title_orig: string | null;
            romaji_orig: string | null;
            image: {
                id: number;
                filename: string;
                height: number;
                nsfw: boolean;
                spoiler: boolean;
                width: number;
            } | null;
            titles: {
                lang: Language;
                romaji: string | null;
                book_id: number;
                official: true;
                title: string;
            }[];
            editions: {
                book_id: number;
                lang: Language | null;
                title: string;
                eid: number;
                staff: {
                    note: string;
                    role_type: "editor" | "staff" | "author" | "artist" | "translator" | "narrator";
                    romaji: string | null;
                    name: string;
                    staff_id: number;
                    staff_alias_id: number;
                }[];
            }[];
            releases: {
                lang: Language;
                id: number;
                romaji: string | null;
                description: string;
                hidden: boolean;
                locked: boolean;
                release_date: number;
                title: string;
                website: string | null;
                amazon: string | null;
                bookwalker: string | null;
                format: "digital" | "print" | "audio";
                isbn13: string | null;
                pages: number | null;
                rakuten: string | null;
            }[];
            publishers: {
                lang: Language;
                id: number;
                romaji: string | null;
                name: string;
                publisher_type: "publisher" | "imprint";
            }[];
            series: {
                books: {
                    id: number;
                    lang: Language;
                    romaji: string | null;
                    title: string;
                    title_orig: string | null;
                    romaji_orig: string | null;
                    image: {
                        id: number;
                        filename: string;
                        height: number;
                        nsfw: boolean;
                        spoiler: boolean;
                        width: number;
                    } | null;
                }[];
                tags: {
                    id: number;
                    name: string;
                    ttype: "tag" | "content" | "demographic" | "genre";
                }[];
                lang: Language;
                id: number;
                romaji: string | null;
                title: string;
                title_orig: string | null;
                romaji_orig: string | null;
            } | undefined
        }
    """
    return await _get(f"/book/{book_id}")


# ----- RELEASES -----


async def get_releases(params: dict[str, Any] | None = None) -> dict:
    """
    Fetch a list of releases with optional filters.

    Args:
        params (dict): Optional query params

    Parameters:
        q: string
        page: number
        limit: number
            Default 24; Max: 100
        rl: Language[]
            Release lanuages
        rll: 'and' | 'or'
            Release lanuages logic
        rf: ('digital' | 'print' | 'audio')[]
            Release formats
        rfl:'and' | 'or'
            Release formats logic
        p: number[]
            The id of publishers
        pl: 'and' | 'or'
            Publisher logic
        sort: 'Relevance desc' | 'Relevance asc' | 'Title asc' | 'Title desc' | 'Release date asc' | 'Release date desc' | 'Pages asc' | 'Pages desc'

    Returns:
        Dict: JSON response

    JSON response structure:
    """
    return await _get("/releases", params)


async def get_release_by_id(release_id: int) -> dict:
    """
    Fetch a release by its ID.

    Args:
        release_id (int): RanobeDB release ID

    Returns:
        Dict: JSON response

    JSON response structure:

        {
            books:  {
                id: number;
                title: string;
                lang: Language;
                romaji: string | null;
                image_id: number | null;
                olang: Language;
                c_release_date: number;
                title_orig: string | null;
                romaji_orig: string | null;
                image: {
                    id: number;
                    filename: string;
                    height: number;
                    nsfw: boolean;
                    spoiler: boolean;
                    width: number;
                } | null;
            }[];
            count: string;
            currentPage: number;
            totalPages: number;
        }
    """
    return await _get(f"/release/{release_id}")


# ----- STAFF -----


async def get_staff(q: str, **kwargs) -> dict:
    """
    Fetch a list of staff by query string.

    Required:
        q (str): Search name

    Optional:
        page: number
        limit: number (max 100)

    Returns:
        Dict: JSON response

    JSON response structure:
        {
            staff: {
                id: number;
                name: string;
                romaji: string | null;
            }[];
            count: string;
            currentPage: number;
            totalPages: number;
        }
    """
    return await _get("/staff", {"q": q, **kwargs})


async def get_staff_by_id(staff_id: int) -> dict:
    """
    Fetch staff details by ID.

    Args:
        staff_id (int): RanobeDB staff ID

    Returns:
        Dict: JSON response

    JSON response structure:
        {
            staff: {
                id: number;
                description: string;
                hidden: boolean;
                locked: boolean;
                bookwalker_id: number | null;
                pixiv_id: number | null;
                twitter_id: string | null;
                website: string | null;
                wikidata_id: number | null;
                romaji: string | null;
                name: string;
                aliases: {
                    id: number;
                    romaji: string | null;
                    main_alias: boolean;
                    name: string;
                    staff_id: number;
                }[];
            };
        }
    """
    return await _get(f"/staff/{staff_id}")


# ----- PUBLISHERS -----


async def get_publishers(q: str, **kwargs) -> dict:
    """
    Fetch a list of publishers by query string.

    Required:
        q (str): Search name

    Optional:
        page: number
        limit: number (max 100)

    Returns:
        Dict: JSON response

    JSON response structure:
        {
            publishers: {
                id: number;
                name: string;
                romaji: string | null;
            }[];
            count: string;
            currentPage: number;
            totalPages: number;
        }
    """
    return await _get("/publishers", {"q": q, **kwargs})


async def get_publisher_by_id(publisher_id: int) -> dict:
    """
    Fetch publisher details by ID.

    Args:
        publisher_id (int): RanobeDB publisher ID

    Returns:
        Dict: JSON response

    JSON response structure:
        {
            publisher: {
                id: number;
                bookwalker: string | null;
                description: string;
                hidden: boolean;
                locked: boolean;
                name: string;
                romaji: string | null;
                twitter_id: string | null;
                website: string | null;
                wikidata_id: number | null;
                child_publishers: {
                    id: number;
                    relation_type: "imprint" | "parent brand" | "parent company" | "subsidiary";
                    name: string;
                    romaji: string | null;
                }[]
            };
        }
    """
    return await _get(f"/publisher/{publisher_id}")


# ----- TAGS -----


async def get_tags(q: str, **kwargs) -> dict:
    """
    Fetch a list of tags by query string.

    Required:
        q (str): Tag keyword

    Optional:
        page: number
        limit: number (max 100)

    Returns:
        Dict: JSON response

    JSON response structure:
        {
            tags: {
                id: number;
                description: string | null;
                name: string;
                ttype: "content" | "demographic" | "genre" | "tag";
                count: string | number | bigint;
            }[];
            count: string;
            totalPages: number;
            currentPage: number;
        }
    """
    return await _get("/tags", {"q": q, **kwargs})
