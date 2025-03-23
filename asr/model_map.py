MODEL_MAP = {
    'af-za': 'chirp_2',
    'cs-cz': 'chirp_2',
    'da-dk': 'chirp_2',
    'de-de': 'chirp_2',
    'en-au': 'chirp_2',
    'en-us': 'chirp_2',
    'en-gb': 'chirp_2',
    'en-in': 'chirp_2',
    'fi-fi': 'chirp_2',
    'fil-ph': 'chirp_2',
    'fr-ca': 'chirp_2',
    'fr-fr': 'chirp_2',
    'gl-es': 'chirp_2',
    'id-id': 'chirp_2',
    'is-is': 'chirp_2',
    'it-it': 'chirp_2',
    'ko-kr': 'chirp_2',
    'lv-lv': 'chirp_2',
    'lt-lt': 'chirp_2',
    'hr-hr': 'chirp_2',
    'hu-hu': 'chirp_2',
    'ms-my': 'chirp_2',
    'nl-nl': 'chirp_2',
    'no-no': 'chirp_2',
    'pt-pt': 'chirp_2',
    'pl-pl': 'chirp_2',
    'ro-ro': 'chirp_2',
    'ru-ru': 'chirp_2',
    'uk-ua': 'chirp_2',
    'es-es': 'chirp_2',
    'es-us': 'chirp_2',
    'sk-sk': 'chirp_2',
    'sl-si': 'chirp_2',
    'sv-se': 'chirp_2',
    'sw-ke': 'chirp_2',
    'tr-tr': 'chirp_2',
    'zu-za': 'chirp_2',
}

LANGUAGE_OVERRIDES = {
    'en-ca': 'en-us', # Cloud Speech V2 dropped en-ca support. chirp_2 is universal, so this is probably close enough.
    'es-mx': 'es-us', # also dropped es-mx, apparently
    'sw-tz': 'sw-ke', # also dropped sw-tz. I don't know enough to know whether this makes sense, to be honest.
    'nb-no': 'no-no', # I'm still pretty sure this one was a typo.
    'auto-auto': 'auto', # this is a special case for the auto-detect language code
}


def get_model_for_lang(code: str) -> str:
    return MODEL_MAP.get(code.lower(), 'chirp_2')

def get_real_lang(code: str) -> str:
    return LANGUAGE_OVERRIDES.get(code.lower(), code.lower())
