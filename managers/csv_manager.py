import csv

class CSVManager:
    def write_csv(self, filename, data):
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(data)

    def read_csv(self, filename):
        with open(filename, mode='r') as file:
            reader = csv.reader(file)
            return list(reader)