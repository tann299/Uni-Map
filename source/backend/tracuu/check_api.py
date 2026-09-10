import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from tracuu.views import _parse_params


def main():
    cases = [
        ({}, 20, 0),
        ({"limit": "100", "offset": "10", "nam": "2025"}, 100, 10),
    ]
    for query, limit, offset in cases:
        params = _parse_params(query)
        assert (params.limit, params.offset) == (limit, offset)

    for query in ({"limit": "0"}, {"nam": "2025"}, {"vung_mien": "Miền Tây"}):
        try:
            _parse_params(query)
        except ValueError:
            pass
        else:
            raise AssertionError(f"phải từ chối {query}")

    print("[OK] query parser")


if __name__ == "__main__":
    main()
