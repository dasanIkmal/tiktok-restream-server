from enum import Enum, IntEnum


class AccountPrivate(Exception):
    pass


class Blacklisted(Exception):
    pass


class UserNotFound(Exception):
    pass


class LiveNotFound(Exception):
    pass


class TimeOut(IntEnum):
    """
    Enumeration that defines timeout values.
    """

    def __mul__(self, operator):
        return self.value * operator

    ONE_MINUTE = 60
    AUTOMATIC_MODE = 5
    CONNECTION_CLOSED = 2


class Error(Enum):
    """
    Enumeration that contains possible errors while using TikTok-Live-Recorder.
    """

    def __str__(self):
        return str(self.value)

    AUTOMATIC_MODE_ERROR: str = "[-] Automatic mode can be used only in unblacklisted country. Use a VPN\n[*] " \
                                "Unrestricted country list: " \
                                "https://github.com/Michele0303/TikTok-Live-Recorder/edit/main/GUIDE.md#unrestricted" \
                                "-country"

    BLACKLIST_ERROR = "[-] Captcha require or country blocked. Use a vpn or room_id." \
                      "\n[-] How to get room id: https://github.com/Michele0303/TikTok-Live-Recorder/blob/main/GUIDE.md#how-to-get-room_id" \
                      "\n[-] Unrestricted country list: https://github.com/Michele0303/TikTok-Live-Recorder/edit/main/GUIDE" \
                      ".md#unrestricted-country"

    USERNAME_ERROR = "[-] Error: Username/Room_id not found or the user has never been in live"

    CONNECTION_CLOSED = "[-] Connection broken by the server."
    CONNECTION_CLOSED_AUTOMATIC = f"{CONNECTION_CLOSED}. Try again after Delay of {TimeOut.CONNECTION_CLOSED} minutes"

    URL_NOT_FOUND = "[-] Unable to find stream url."
    LIVE_NOT_FOUND = "The link provided is not a live tiktok"



