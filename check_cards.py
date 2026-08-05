"""Check if card IDs in deck exist in CSV."""

import csv

deck_ids = [22, 24, 25, 27, 28, 1077, 1078, 1079, 1080, 1081, 6, 1]

with open('EN_Card_Data.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    
found = set()
for row in rows:
    try:
        card_id = int(row['Card ID'])
        if card_id in deck_ids:
            found.add(card_id)
            print(f'Card {card_id}: {row["Card Name"]} ({row["Stage (Pokémon)/Type (Energy and Trainer)"][:30]}...)')
    except ValueError:
        continue

missing = set(deck_ids) - found
print(f'\nMissing cards: {missing}')