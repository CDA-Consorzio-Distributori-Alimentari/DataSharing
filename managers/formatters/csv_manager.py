import csv
from pathlib import Path
from io import StringIO

class CSVManager:
    def build_csv_content(self, data):
        buffer = StringIO(newline='')
        writer = csv.writer(buffer)
        writer.writerows(data)
        return buffer.getvalue()

    def write_csv(self, filename, data):
        csv_content = self.build_csv_content(data)
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            file.write(csv_content)
        return csv_content

    def read_csv(self, filename):
        with open(filename, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            return list(reader)