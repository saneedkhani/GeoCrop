"""USDA Cropland Data Layer class names (crop classes from the training script, plus land-cover classes)."""

CDL_CROP_NAMES = {
    1: "Corn", 2: "Cotton", 3: "Rice", 4: "Sorghum", 5: "Soybeans",
    6: "Sunflower", 10: "Peanuts", 11: "Tobacco", 12: "Sweet Corn",
    13: "Pop or Orn Corn", 14: "Mint", 21: "Barley", 22: "Durum Wheat",
    23: "Spring Wheat", 24: "Winter Wheat", 25: "Other Small Grains",
    26: "Winter Wheat/Soybeans", 27: "Rye", 28: "Oats", 29: "Millet",
    30: "Speltz", 31: "Canola", 32: "Flaxseed", 33: "Safflower",
    34: "Rape Seed", 35: "Mustard", 36: "Alfalfa", 37: "Other Hay/Non Alfalfa",
    38: "Camelina", 39: "Buckwheat", 41: "Sugarbeets", 42: "Dry Beans",
    43: "Potatoes", 44: "Other Crops", 45: "Sugarcane", 46: "Sweet Potatoes",
    47: "Misc Vegs & Fruits", 48: "Watermelons", 49: "Onions", 50: "Cucumbers",
    51: "Chick Peas", 52: "Lentils", 53: "Peas", 54: "Tomatoes",
    55: "Caneberries", 56: "Hops", 57: "Herbs", 58: "Clover/Wildflowers",
    59: "Sod/Grass Seed", 61: "Fallow/Idle Cropland", 66: "Cherries",
    67: "Peaches", 68: "Apples", 69: "Grapes", 70: "Christmas Trees",
    71: "Other Tree Crops", 72: "Citrus", 74: "Pecans", 75: "Almonds",
    76: "Walnuts", 77: "Pears", 204: "Pistachios", 205: "Triticale",
    206: "Carrots", 207: "Asparagus", 208: "Garlic", 209: "Cantaloupes",
    210: "Prunes", 211: "Olives", 212: "Oranges", 213: "Honeydew Melons",
    214: "Broccoli", 216: "Peppers", 217: "Pomegranates", 218: "Nectarines",
    219: "Greens", 220: "Plums", 221: "Strawberries", 222: "Squash",
    223: "Apricots", 224: "Vetch", 225: "Winter Wheat/Corn", 226: "Sweet Corn/Corn",
    227: "Lettuce", 228: "Oats/Corn", 229: "Pumpkins", 242: "Blueberries",
    243: "Cabbage", 244: "Cauliflower", 245: "Celery", 246: "Radishes",
    247: "Turnips", 248: "Eggplants", 249: "Gourds", 250: "Cranberries",
}

CDL_LANDCOVER_NAMES = {
    111: "Open Water", 112: "Perennial Ice/Snow", 121: "Developed/Open Space", 122: "Developed/Low Intensity",
    123: "Developed/Med Intensity", 124: "Developed/High Intensity", 131: "Barren", 141: "Deciduous Forest",
    142: "Evergreen Forest", 143: "Mixed Forest", 152: "Shrubland", 176: "Grassland/Pasture",
    190: "Woody Wetlands", 195: "Herbaceous Wetlands",
}

CDL_NAMES = {**CDL_CROP_NAMES, **CDL_LANDCOVER_NAMES}
