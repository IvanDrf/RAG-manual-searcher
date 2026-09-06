import os

import pdfplumber
from tqdm import tqdm

# Create array of name books from student_books_pdf
array_name_books = [book for book in os.listdir("./student_book_pdf")]

# Convert pdf to txt
for book in tqdm(array_name_books):
    name_book = book.split(".")[0]
    with (
        pdfplumber.open(f"./student_book_pdf/{name_book}.pdf") as pdf,
        open(f"./student_book_txt/{name_book}.txt", "w", encoding="utf-8") as file,
    ):
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                file.write(t + "\n")
