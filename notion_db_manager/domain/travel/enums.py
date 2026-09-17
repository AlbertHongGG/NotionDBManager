from enum import Enum

class PhotoProviderType(str, Enum):
    PLAYWRIGHT = "playwright"
    GOOGLE = "google"
