from multiprocessing import context
from pathlib import Path
import os
import re
import pdfplumber
from tqdm import tqdm

def convert_pdf_to_txt():
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

def fixing_bad_words_in_txt():

    array_txt_books = [book for book in os.listdir('./student_book_txt')]

    for book in tqdm(array_txt_books):
        with open(f"./student_book_txt/{book}", mode='r+', encoding='utf-8') as file:
            content = file.read()

            cleaned_content = re.sub(r"^.*[À-ÿ].*$\n?", "", content, flags=re.MULTILINE)

            file.seek(0)

            file.write(cleaned_content)

            file.truncate()

if __name__ == "__main__":
    fixing_bad_words_in_txt()
