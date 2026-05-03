from random import randint

COLOR_HIGHLIGHTED_PINK = (239, 87, 119)
COLOR_DARK_PERIWINKLE = (87, 95, 207)
COLOR_MEGAMAN = (75, 207, 250)
COLOR_FRESH_TURQUOISE = (52, 231, 228)

COLOR_MINTY_GREEN = (11, 232, 129)
COLOR_SIZZLING_RED = (245, 59, 87)
COLOR_FREE_SPEECH_BLUE = (60, 64, 198)
COLOR_SPIRO_DISCO_BALL = (15, 188, 249)

COLOR_JADE_DUST = (0, 216, 214)
COLOR_GREEN_TEAL = (5, 196, 107)
COLOR_NARENJI_ORANGE = (255, 192, 72)
COLOR_YRIEL_YELLOW = (255, 221, 89)

COLOR_SUNSET_ORANGE = (255, 94, 87)
COLOR_HINT_OF_ELUSIVE_BLUE = (210, 218, 226)
COLOR_GOOD_NIGHT = (72, 84, 96)
COLOR_CHROME_YELLOW = (255, 168, 1)

COLOR_VIBRANT_YELLOW = (255, 211, 42)
COLOR_RED_ORANGE = (255, 63, 52)
COLOR_LONDON_SQUARE = (128, 142, 155)
COLOR_BLACK_PEARL = (30, 39, 46)


COLOR_RED = (255, 0, 0)
COLOR_YELLOW = (255, 255, 0)
COLOR_BLUE = (0, 0, 255)

def get_color_for_temperature(temperature: float) -> tuple[int, int, int]:
    if temperature > 30:
        return COLOR_RED
    elif temperature > 28:
        return COLOR_YELLOW
    elif temperature < 18:
        return COLOR_BLUE
    else:
        return (randint(0,255), randint(0,255), randint(0,255))