MODEL_MAP = {
    'af-za': 'default',  # latest_short not supported
    'cs-cz': 'latest_short',
    'da-dk': 'latest_short',
    'de-de': 'latest_short',
    'en-au': 'latest_short',
    'en-us': 'latest_short',
    'en-gb': 'latest_short',
    'en-in': 'latest_short',
    'en-ca': 'default',  # latest_short not supported
    'fi-fi': 'latest_short',
    'fil-ph': 'default',  # latest_short not supported
    'fr-ca': 'latest_short',
    'fr-fr': 'latest_short',
    'gl-es': 'default',  # latest_short not supported
    'id-id': 'latest_short',
    'is-is': 'default',  # latest_short not supported
    'it-it': 'latest_short',
    'ko-kr': 'latest_short',
    'lv-lv': 'default',  # latest_short not supported
    'lt-lt': 'default',  # latest_short not supported
    'hr-hr': 'default',  # latest_short not supported
    'hu-hu': 'default',  # latest_short not supported
    'ms-my': 'default',  # latest_short not supported
    'nl-nl': 'latest_short',
    'nb-no': 'default',  # this isn't listed at all. Did we mean no_NO?
    'no-no': 'latest_short',
    'pt-pt': 'latest_short',
    'pl-pl': 'latest_short',
    'ro-ro': 'latest_short',
    'ru-ru': 'latest_short',
    'es-es': 'latest_short',
    'es-mx': 'default',  # latest_short not supported
    'es-us': 'latest_short',
    'sk-sk': 'default',  # latest_short not supported
    'sl-sl': 'default',  # this doesn't seem to exist
    'sl-si': 'default',  # latest_short not supported
    'sv-se': 'latest_short',
    'sw-tz': 'default',  # latest_short not supported
    'sw-ke': 'default',  # latest_short not supported
    'tr-tr': 'default',  # latest_short lacks automatic punctuation
    'zu-za': 'default',  # latest_short not supported
}


def get_model_for_lang(code: str) -> str:
    return MODEL_MAP.get(code.lower(), 'default')
