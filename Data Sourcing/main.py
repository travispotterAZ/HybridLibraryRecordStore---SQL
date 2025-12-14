import time #for runtime

from spotify.client import get_spotify_client   #authentication
from spotify.fetch import search_ALBUMS_by_artists       #search spotify database
from utils.export import export_record_list     #exporting to csv

PopularGenres = [
    "pop",
    "hip hop",
    "rap",
    "trap",
    "drill",
    "rock",
    "alternative rock",
    "hard rock",
    "punk",
    "metal",
    "heavy metal",
    "death metal",
    "country",
    "americana",
    "folk",
    "indie",
    "indie pop",
    "indie rock",
    "edm",
    "house",
    "techno",
    "trance",
    "dubstep",
    "drum and bass",
    "latin",
    "reggaeton",
    "salsa",
    "banda",
    "k-pop",
    "j-pop",
    "r&b",
    "soul",
    "funk",
    "jazz",
    "smooth jazz",
    "classical",
    "opera",
    "soundtrack",
    "ambient",
    "lofi",
    "reggae",
    "afrobeats",
    "world",
    "blues",
    "gospel",
    "christian",
    "new age"
]

allRecords = []
#SetUp
sp = get_spotify_client()   #this is the authenticated spotify client

#Search_time Start
start_time = time.time()

#Record Fetch
query = ""
limit = 75

for idx, genre in enumerate(PopularGenres, start=1):
    print(f"[{idx}/{len(PopularGenres)}] Searching genre: {genre} ...")
    records = search_ALBUMS_by_artists(sp, query=genre, artist_lim=50)
    allRecords.extend(records)
    print(f"   → Retrieved {len(records)} new records (total: {len(allRecords)})")


#Search_time end
end_time = time.time()
search_time = end_time - start_time
print(f"Exported {len(allRecords)} records to data/records.csv")
print(f"Runtime: {search_time:.2f} seconds")

#Export to CSV
export_record_list(allRecords, "data/records.csv")