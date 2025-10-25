import csv
from typing import Dict, List

def save_to_csv(data: List[Dict[str, str]], headers: List[str], filename: str = "output.csv") -> None:
    with open(filename, mode="w", newline='', encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        
        for row in data:
            # Build row using headers to ensure consistency and default to ""
            formatted_row = {
                "Name": row.get("Name", "NA"),
                "Industry": row.get("Industry", "NA"),
                "Address": row.get("Address", "NA"),
                "Rating": row.get("Rating", "NA"),
                "BBB_rating": row.get("BBB_rating", "NA"),
                "Business_phone": row.get("Business_phone", "NA"),
                "Website": row.get("Website", "NA")
            }
            writer.writerow(formatted_row)

    print(f"Data saved to {filename}")


def merge_data_sources(fieldnames: List[str],
                       data1: List[Dict[str, str]] = [],
                       data2: List[Dict[str, str]] = [],
                       data3: List[Dict[str, str]] = [],
                       data4: List[Dict[str, str]] = [],
                       data5: List[Dict[str, str]] = []) -> List[Dict[str, str]]:
    merged = []
    seen_keys = set()

    def get_key(record: Dict[str, str]) -> str:
        company = record.get("Company", "").strip().lower()
        address = record.get("Address", "").replace("[G]", "").strip().lower()
        return company + address

    def add_record(record: Dict[str, str]):
        if not isinstance(record, dict):
            print(f"[WARN] Skipping invalid record: {record}")
            return
        key = get_key(record)
        if key not in seen_keys:
            seen_keys.add(key)
            normalized_record = {field: record.get(field, "NA") for field in fieldnames}
            merged.append(normalized_record)

    for data in (data1, data2, data3, data4, data5):
        for record in data:
            add_record(record)

    return merged
