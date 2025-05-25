import sqlite3
import re

DB_PATH = 'Site/TestSite/database.db'  # путь к вашей базе

def extract_date_from_filename(filename):
    # Ищем шаблон даты вида 01-03-2024_06-48
    match = re.search(r'(\d{2})-(\d{2})-(\d{4})_(\d{2})-(\d{2})', filename)
    if match:
        day, month, year, hour, minute = match.groups()
        # Формируем строку даты в формате YYYY-MM-DD HH:MM:00
        return f"{year}-{month}-{day} {hour}:{minute}:00"
    return None

def update_dates():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename FROM image_data")
    rows = cursor.fetchall()
    updated = 0

    for row in rows:
        id, filename = row
        new_date = extract_date_from_filename(filename)
        if new_date:
            cursor.execute("UPDATE image_data SET file_date = ? WHERE id = ?", (new_date, id))
            updated += 1

    conn.commit()
    conn.close()
    print(f"Обновлено {updated} записей.")

if __name__ == '__main__':
    update_dates()