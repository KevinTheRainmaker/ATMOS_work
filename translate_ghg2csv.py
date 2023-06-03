import zipfile
import chardet
import csv

zip_file = '2023-06-02T000000_AIU-1905.ghg'

input_file = '2023-06-02T000000_AIU-1905.data'
output_file = 'ghg_data.csv'

with zipfile.ZipFile(zip_file, 'r') as zip_ref:
    zip_ref.extract(input_file)

with open(input_file, 'rb') as file:
    result = chardet.detect(file.read())

encoding = result['encoding']

with open(input_file, 'r', encoding=encoding) as data_file, open(output_file, 'w', newline='', encoding='utf-8') as csv_file:
    writer = csv.writer(csv_file)

    for line in data_file:
        line = line.strip()

        if line.startswith('#') or not line:
            continue

        data = line.split('\t')

        writer.writerow(data)

print("CSV 파일로 변환되었습니다.")
